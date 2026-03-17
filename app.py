from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import random
import os

from models import db, User, Progress, CompletedExercise, CustomExercise, FlashcardStudy, Achievement, UserAchievement, DailyGoal, PracticeSession, Notification
from utils import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui_cambiala_en_produccion'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///comunicacion.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'

# ============================================
# LOADER DE USUARIO
# ============================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================================
# RUTAS PRINCIPALES
# ============================================

@app.route('/')
def index():
    """Página de inicio"""
    return render_template('index.html')

@app.route('/teoria')
def teoria():
    """Página de teoría"""
    return render_template('teoria.html')

# ============================================
# RUTAS DE EJERCICIOS
# ============================================

@app.route('/ejercicios')
@login_required
def ejercicios():
    """Página principal de ejercicios"""
    # Obtener progreso del usuario
    progress = Progress.query.filter_by(user_id=current_user.id).first()
    if not progress:
        progress = Progress(user_id=current_user.id)
        db.session.add(progress)
        db.session.commit()
    
    # Estadísticas por tipo
    type_stats = {
        'transformacion': progress.get_type_accuracy('transformacion'),
        'completar': progress.get_type_accuracy('completar'),
        'identificar': progress.get_type_accuracy('identificar')
    }
    
    return render_template('ejercicios.html', 
                         progress=progress,
                         type_stats=type_stats)

@app.route('/api/ejercicio/<tipo>')
@login_required
def get_ejercicio(tipo):
    """Obtener un ejercicio aleatorio"""
    # Obtener IDs de ejercicios recientes para evitar repetición
    recent = CompletedExercise.query.filter_by(
        user_id=current_user.id
    ).order_by(CompletedExercise.completed_at.desc()).limit(10).all()
    recent_ids = [r.exercise_id for r in recent]
    
    # Obtener ejercicios personalizados del usuario
    custom = CustomExercise.query.filter_by(user_id=current_user.id, type=tipo).all()
    
    # Obtener ejercicio aleatorio
    exercise = get_random_exercise(
        exercise_type=tipo,
        exclude_ids=recent_ids
    )
    
    if not exercise and not custom:
        return jsonify({'error': 'No hay ejercicios disponibles'}), 404
    
    # Si hay ejercicios personalizados, incluirlos ocasionalmente
    if custom and random.random() < 0.3:  # 30% de probabilidad
        custom_ex = random.choice(custom)
        return jsonify({
            'id': f"custom_{custom_ex.id}",
            'tipo': custom_ex.type,
            'frase': custom_ex.phrase,
            'respuesta': custom_ex.answer,
            'dificultad': custom_ex.difficulty,
            'categoria': custom_ex.category or 'personalizado',
            'puntos': 15,
            'estrellas_max': 4,
            'explicacion': 'Ejercicio personalizado creado por ti.',
            'es_personalizado': True
        })
    
    return jsonify(exercise)

@app.route('/api/ejercicio/verificar', methods=['POST'])
@login_required
def verificar_ejercicio():
    """Verificar respuesta de ejercicio"""
    data = request.json
    exercise_id = data.get('exercise_id')
    user_answer = data.get('answer', '').strip().lower()
    time_spent = data.get('time_spent', 0)
    
    # Verificar si es ejercicio personalizado
    if str(exercise_id).startswith('custom_'):
        custom_id = int(str(exercise_id).replace('custom_', ''))
        exercise = CustomExercise.query.get(custom_id)
        if not exercise:
            return jsonify({'error': 'Ejercicio no encontrado'}), 404
        
        correct_answer = exercise.answer.lower()
        exercise_type = exercise.type
        exercise_category = exercise.category or 'personalizado'
        exercise_difficulty = exercise.difficulty
        max_points = 15
        
        # Actualizar estadísticas del ejercicio personalizado
        exercise.times_used += 1
        if user_answer == correct_answer:
            exercise.times_correct += 1
    
    else:
        # Ejercicio predefinido
        exercise_id = int(exercise_id)
        exercises = load_exercises()
        exercise = next((e for e in exercises if e['id'] == exercise_id), None)
        
        if not exercise:
            return jsonify({'error': 'Ejercicio no encontrado'}), 404
        
        correct_answer = exercise['respuesta'].lower()
        exercise_type = exercise['tipo']
        exercise_category = exercise['categoria']
        exercise_difficulty = exercise['dificultad']
        max_points = exercise['puntos']
    
    correct = (user_answer == correct_answer)
    points = max_points if correct else 0
    stars = calculate_stars(points, time_spent, max_points, 100 if correct else 0)
    exp_points = calculate_experience(points, stars, time_spent)
    
    # Registrar ejercicio completado
    completed = CompletedExercise(
        user_id=current_user.id,
        exercise_id=exercise_id if not str(exercise_id).startswith('custom_') else 0,
        exercise_type=exercise_type,
        exercise_category=exercise_category,
        exercise_difficulty=exercise_difficulty,
        correct=correct,
        points_earned=points,
        stars_earned=stars,
        time_spent=time_spent
    )
    db.session.add(completed)
    
    # Actualizar progreso
    progress = current_user.progress
    if not progress:
        progress = Progress(user_id=current_user.id)
        db.session.add(progress)
    
    progress.exercises_attempted += 1
    progress.total_time_spent += time_spent
    
    # Actualizar estadísticas por tipo
    type_attempts = getattr(progress, f"{exercise_type}_attempts", 0) + 1
    setattr(progress, f"{exercise_type}_attempts", type_attempts)
    
    if correct:
        progress.exercises_correct += 1
        current_user.total_score += points
        current_user.total_stars += stars
        current_user.add_experience(exp_points)
        
        type_correct = getattr(progress, f"{exercise_type}_correct", 0) + 1
        setattr(progress, f"{exercise_type}_correct", type_correct)
        
        # Actualizar estadísticas por categoría
        progress.update_category_stats(exercise_category, correct)
    
    # Registrar en meta diaria
    daily = update_daily_goal(
        current_user,
        exercises_completed=1,
        correct=correct,
        points=points,
        stars=stars,
        time_spent=time_spent
    )
    
    db.session.commit()
    
    # Verificar logros
    new_achievements = check_achievements(current_user)
    
    # Actualizar racha
    streak = update_streak(current_user)
    
    # Obtener progreso actualizado
    progress = current_user.progress
    
    return jsonify({
        'correct': correct,
        'points': points,
        'stars': stars,
        'exp_points': exp_points,
        'total_score': current_user.total_score,
        'total_stars': current_user.total_stars,
        'level': current_user.level,
        'level_progress': current_user.get_level_progress(),
        'accuracy': progress.get_accuracy(),
        'daily_progress': daily.exercises_completed,
        'daily_goal': progress.daily_goal,
        'daily_achieved': daily.goal_achieved,
        'streak': streak,
        'new_achievements': [{'name': a.name, 'icon': a.icon} for a in new_achievements],
        'explicacion': exercise['explicacion'] if not str(exercise_id).startswith('custom_') else exercise.answer
    })

# ============================================
# RUTAS DE FLASHCARDS
# ============================================

@app.route('/flashcards')
@login_required
def flashcards():
    """Página de flashcards"""
    category = request.args.get('categoria', None)
    
    # Obtener flashcards para repasar
    due = get_due_flashcards(current_user, limit=5)
    
    # Si no hay para repasar, obtener una aleatoria
    if not due:
        flashcard = get_random_flashcard(category)
        study = None
    else:
        item = due[0]
        flashcard = item['flashcard']
        study = item['study']
    
    # Estadísticas
    mastered = FlashcardStudy.query.filter_by(
        user_id=current_user.id,
        mastered=True
    ).count()
    
    total_studied = FlashcardStudy.query.filter_by(user_id=current_user.id).count()
    
    return render_template('flashcards.html', 
                         flashcard=flashcard,
                         study=study,
                         category=category,
                         mastered=mastered,
                         total_studied=total_studied)

@app.route('/api/flashcard/next')
@login_required
def next_flashcard():
    """Obtener siguiente flashcard"""
    category = request.args.get('categoria')
    
    # Obtener flashcards para repasar
    due = get_due_flashcards(current_user, limit=1)
    
    if due:
        item = due[0]
        flashcard = item['flashcard']
        study = item['study']
    else:
        # Obtener flashcards no estudiadas
        studied_ids = [s.flashcard_id for s in FlashcardStudy.query.filter_by(user_id=current_user.id)]
        flashcard = get_random_flashcard(category, exclude_ids=studied_ids)
        
        if not flashcard:
            # Si ya estudió todas, repasar algunas
            flashcard = get_random_flashcard(category)
        
        # Crear registro de estudio
        study = FlashcardStudy(
            user_id=current_user.id,
            flashcard_id=flashcard['id'],
            flashcard_category=flashcard['categoria'],
            last_reviewed=datetime.utcnow(),
            next_review=datetime.utcnow() + timedelta(days=1)
        )
        db.session.add(study)
        db.session.commit()
    
    return jsonify({
        'flashcard': flashcard,
        'study_id': study.id if study else None
    })

@app.route('/api/flashcard/review/<int:study_id>', methods=['POST'])
@login_required
def review_flashcard(study_id):
    """Registrar revisión de flashcard"""
    data = request.json
    quality = data.get('quality', 3)  # 0-5, donde 5 es perfecto
    
    study = FlashcardStudy.query.get_or_404(study_id)
    
    if study.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403
    
    study.update_review(quality)
    
    # Si ha sido revisada muchas veces, considerar dominada
    if study.times_reviewed >= 5 and study.times_correct / study.times_reviewed >= 0.8:
        study.mastered = True
        current_user.progress.flashcards_mastered += 1
    
    current_user.progress.flashcards_studied += 1
    db.session.commit()
    
    return jsonify({
        'success': True,
        'mastered': study.mastered,
        'next_review': study.next_review.isoformat()
    })

# ============================================
# RUTAS DE PRÁCTICA PERSONALIZADA
# ============================================

@app.route('/practica')
@login_required
def practica():
    """Página de práctica personalizada"""
    count = int(request.args.get('count', 5))
    exercises = get_recommended_exercises(current_user, count)
    
    # Iniciar sesión de práctica
    session = start_practice_session(current_user)
    
    return render_template('practica.html', 
                         exercises=exercises,
                         session_id=session.id)

@app.route('/api/practica/finalizar/<int:session_id>', methods=['POST'])
@login_required
def finalizar_practica(session_id):
    """Finalizar sesión de práctica"""
    data = request.json
    session = PracticeSession.query.get_or_404(session_id)
    
    if session.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403
    
    session.exercises_completed = data.get('completed', 0)
    session.exercises_correct = data.get('correct', 0)
    session.points_earned = data.get('points', 0)
    session.stars_earned = data.get('stars', 0)
    session.exercise_types = json.dumps(data.get('types', []))
    session.end_session()
    
    # Actualizar progreso
    progress = current_user.progress
    progress.practice_sessions += 1
    progress.practice_time += session.total_time // 60
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'total_time': session.total_time,
        'accuracy': (session.exercises_correct / session.exercises_completed * 100) if session.exercises_completed else 0
    })

# ============================================
# RUTAS DE PROGRESO
# ============================================

@app.route('/progreso')
@login_required
def progreso():
    """Página de progreso"""
    progress = current_user.progress
    
    # Obtener últimos ejercicios
    recent = CompletedExercise.query.filter_by(
        user_id=current_user.id
    ).order_by(CompletedExercise.completed_at.desc()).limit(10).all()
    
    # Obtener estadísticas
    stats = get_user_stats(current_user, days=30)
    
    # Obtener racha
    streak = current_user.current_streak
    
    # Obtener meta diaria actual
    today = datetime.utcnow().date()
    daily = DailyGoal.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()
    
    return render_template('progreso.html',
                         progress=progress,
                         recent=recent,
                         stats=stats,
                         streak=streak,
                         daily=daily)

@app.route('/api/progreso/estadisticas')
@login_required
def get_estadisticas():
    """Obtener estadísticas en formato JSON"""
    days = int(request.args.get('days', 30))
    stats = get_user_stats(current_user, days)
    return jsonify(stats)

# ============================================
# RUTAS DE LOGROS
# ============================================

@app.route('/logros')
@login_required
def logros():
    """Página de logros"""
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
    all_achievements = Achievement.query.order_by(Achievement.order).all()
    
    unlocked_ids = [ua.achievement_id for ua in user_achievements]
    
    # Separar en desbloqueados y bloqueados
    unlocked = []
    locked = []
    
    for achievement in all_achievements:
        if achievement.id in unlocked_ids:
            ua = next(ua for ua in user_achievements if ua.achievement_id == achievement.id)
            unlocked.append({
                'achievement': achievement,
                'unlocked_at': ua.unlocked_at
            })
        else:
            # Calcular progreso
            progress = 0
            if achievement.points_required > 0:
                progress = min(100, int((current_user.total_score / achievement.points_required) * 100))
            elif achievement.exercises_required > 0:
                progress = min(100, int((current_user.progress.exercises_correct / achievement.exercises_required) * 100))
            elif achievement.streak_required > 0:
                progress = min(100, int((current_user.current_streak / achievement.streak_required) * 100))
            elif achievement.custom_exercises_required > 0:
                custom_count = CustomExercise.query.filter_by(user_id=current_user.id).count()
                progress = min(100, int((custom_count / achievement.custom_exercises_required) * 100))
            elif achievement.flashcards_mastered_required > 0:
                progress = min(100, int((current_user.progress.flashcards_mastered / achievement.flashcards_mastered_required) * 100))
            
            locked.append({
                'achievement': achievement,
                'progress': progress
            })
    
    return render_template('logros.html',
                         unlocked=unlocked,
                         locked=locked)

# ============================================
# RUTAS DE RANKING
# ============================================

@app.route('/ranking')
@login_required
def ranking():
    """Página de ranking"""
    by = request.args.get('by', 'score')
    top_users = get_leaderboard(20, by)
    user_rank = get_user_rank(current_user, by)
    
    return render_template('ranking.html',
                         top_users=top_users,
                         user_rank=user_rank,
                         ranking_by=by)

# ============================================
# RUTAS DE CREADOR DE EJERCICIOS
# ============================================

@app.route('/creador', methods=['GET', 'POST'])
@login_required
def creador():
    """Página de creación de ejercicios personalizados"""
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        frase = request.form.get('frase')
        respuesta = request.form.get('respuesta')
        dificultad = request.form.get('dificultad', 'media')
        categoria = request.form.get('categoria', 'personalizado')
        
        # Verificar límite de 100 ejercicios
        count = CustomExercise.query.filter_by(user_id=current_user.id).count()
        if count >= 100:
            flash('Has alcanzado el límite de 100 ejercicios personalizados.', 'warning')
            return redirect(url_for('creador'))
        
        # Validar campos
        if not frase or not respuesta:
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('creador'))
        
        exercise = CustomExercise(
            user_id=current_user.id,
            type=tipo,
            phrase=frase,
            answer=respuesta,
            difficulty=dificultad,
            category=categoria
        )
        db.session.add(exercise)
        db.session.commit()
        
        flash('Ejercicio guardado correctamente. +10 puntos por crear.', 'success')
        current_user.total_score += 10
        db.session.commit()
        
        # Verificar logros (por si alcanzó el de creador)
        check_achievements(current_user)
        
        return redirect(url_for('creador'))
    
    # Obtener ejercicios del usuario
    exercises = CustomExercise.query.filter_by(user_id=current_user.id).order_by(
        CustomExercise.created_at.desc()
    ).all()
    
    # Estadísticas
    total_created = len(exercises)
    most_used = CustomExercise.query.filter_by(user_id=current_user.id).order_by(
        CustomExercise.times_used.desc()
    ).first()
    
    return render_template('creador.html',
                         exercises=exercises,
                         total_created=total_created,
                         most_used=most_used)

@app.route('/api/creador/eliminar/<int:exercise_id>', methods=['DELETE'])
@login_required
def eliminar_ejercicio_personalizado(exercise_id):
    """Eliminar ejercicio personalizado"""
    exercise = CustomExercise.query.get_or_404(exercise_id)
    
    if exercise.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403
    
    db.session.delete(exercise)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/creador/editar/<int:exercise_id>', methods=['PUT'])
@login_required
def editar_ejercicio_personalizado(exercise_id):
    """Editar ejercicio personalizado"""
    exercise = CustomExercise.query.get_or_404(exercise_id)
    
    if exercise.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403
    
    data = request.json
    exercise.phrase = data.get('phrase', exercise.phrase)
    exercise.answer = data.get('answer', exercise.answer)
    exercise.difficulty = data.get('difficulty', exercise.difficulty)
    exercise.category = data.get('category', exercise.category)
    exercise.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True})

# ============================================
# RUTAS DE PERFIL
# ============================================

@app.route('/perfil')
@login_required
def perfil():
    """Página de perfil de usuario"""
    return render_template('perfil.html')

@app.route('/api/perfil/actualizar', methods=['POST'])
@login_required
def actualizar_perfil():
    """Actualizar perfil de usuario"""
    data = request.json
    
    if 'language' in data:
        current_user.language = data['language']
    
    if 'daily_goal' in data:
        current_user.progress.daily_goal = data['daily_goal']
    
    if 'weekly_goal' in data:
        current_user.progress.weekly_goal = data['weekly_goal']
    
    db.session.commit()
    
    return jsonify({'success': True})

# ============================================
# RUTAS DE NOTIFICACIONES
# ============================================

@app.route('/api/notificaciones')
@login_required
def get_notificaciones():
    """Obtener notificaciones del usuario"""
    unread = get_unread_notifications(current_user.id)
    return jsonify([{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'icon': n.icon,
        'color': n.color,
        'created_at': n.created_at.isoformat()
    } for n in unread])

@app.route('/api/notificaciones/leer', methods=['POST'])
@login_required
def marcar_notificaciones_leidas():
    """Marcar notificaciones como leídas"""
    mark_notifications_as_read(current_user.id)
    return jsonify({'success': True})

# ============================================
# RUTAS DE AUTENTICACIÓN
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            user.last_active = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        
        flash('Usuario o contraseña incorrectos.', 'danger')
    
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    """Página de registro"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validaciones
        if not username or not email or not password:
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('registro'))
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('registro'))
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return redirect(url_for('registro'))
        
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está en uso.', 'danger')
            return redirect(url_for('registro'))
        
        if User.query.filter_by(email=email).first():
            flash('El email ya está registrado.', 'danger')
            return redirect(url_for('registro'))
        
        # Crear usuario
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        
        # Crear progreso inicial
        progress = Progress(user_id=user.id)
        db.session.add(progress)
        
        db.session.commit()
        
        flash('Registro exitoso. ¡Bienvenido!', 'success')
        return redirect(url_for('login'))
    
    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    logout_user()
    return redirect(url_for('index'))

# ============================================
# RUTAS DE ADMINISTRACIÓN (solo para desarrollo)
# ============================================

@app.route('/admin/init-db')
def init_db():
    """Inicializar base de datos con datos de ejemplo (solo desarrollo)"""
    if app.config['ENV'] == 'development':
        db.create_all()
        
        # Crear logros si no existen
        if Achievement.query.count() == 0:
            achievements = [
                Achievement(
                    name='Primeros Pasos',
                    description='Completar 10 ejercicios correctamente',
                    icon='bi-star',
                    category='ejercicios',
                    exercises_required=10,
                    reward_points=50,
                    reward_stars=5,
                    badge_color='bronze',
                    order=1
                ),
                Achievement(
                    name='Aprendiz',
                    description='Alcanzar 100 puntos',
                    icon='bi-book',
                    category='puntos',
                    points_required=100,
                    reward_points=100,
                    reward_stars=10,
                    badge_color='bronze',
                    order=2
                ),
                Achievement(
                    name='Comunicador',
                    description='Alcanzar 250 puntos',
                    icon='bi-chat',
                    category='puntos',
                    points_required=250,
                    reward_points=150,
                    reward_stars=15,
                    badge_color='silver',
                    order=3
                ),
                Achievement(
                    name='Experto',
                    description='Alcanzar 500 puntos',
                    icon='bi-trophy',
                    category='puntos',
                    points_required=500,
                    reward_points=200,
                    reward_stars=20,
                    badge_color='gold',
                    order=4
                ),
                Achievement(
                    name='Creador',
                    description='Crear 5 ejercicios personalizados',
                    icon='bi-pencil',
                    category='creador',
                    custom_exercises_required=5,
                    reward_points=100,
                    reward_stars=10,
                    badge_color='bronze',
                    order=5
                ),
                Achievement(
                    name='Creador Experto',
                    description='Crear 20 ejercicios personalizados',
                    icon='bi-pencil-fill',
                    category='creador',
                    custom_exercises_required=20,
                    reward_points=200,
                    reward_stars=20,
                    badge_color='silver',
                    order=6
                ),
                Achievement(
                    name='Racha de 7 días',
                    description='Practicar 7 días seguidos',
                    icon='bi-calendar-check',
                    category='racha',
                    streak_required=7,
                    reward_points=100,
                    reward_stars=10,
                    badge_color='bronze',
                    order=7
                ),
                Achievement(
                    name='Racha de 30 días',
                    description='Practicar 30 días seguidos',
                    icon='bi-calendar-week',
                    category='racha',
                    streak_required=30,
                    reward_points=300,
                    reward_stars=30,
                    badge_color='gold',
                    order=8
                ),
                Achievement(
                    name='Maestro de Flashcards',
                    description='Estudiar 50 flashcards',
                    icon='bi-card-list',
                    category='flashcards',
                    flashcards_mastered_required=50,
                    reward_points=150,
                    reward_stars=15,
                    badge_color='silver',
                    order=9
                ),
                Achievement(
                    name='Experto en Flashcards',
                    description='Estudiar 100 flashcards',
                    icon='bi-card-heading',
                    category='flashcards',
                    flashcards_mastered_required=100,
                    reward_points=300,
                    reward_stars=30,
                    badge_color='gold',
                    order=10
                ),
                Achievement(
                    name='Perfeccionista',
                    description='Obtener 5 estrellas en 20 ejercicios',
                    icon='bi-stars',
                    category='calidad',
                    exercises_required=20,
                    reward_points=200,
                    reward_stars=25,
                    badge_color='gold',
                    order=11
                ),
                Achievement(
                    name='Transformador',
                    description='Completar 50 ejercicios de transformación',
                    icon='bi-arrow-repeat',
                    category='tipo',
                    exercises_required=50,
                    reward_points=150,
                    reward_stars=15,
                    badge_color='silver',
                    order=12
                ),
                Achievement(
                    name='Completador',
                    description='Completar 50 ejercicios de completar',
                    icon='bi-pencil-square',
                    category='tipo',
                    exercises_required=50,
                    reward_points=150,
                    reward_stars=15,
                    badge_color='silver',
                    order=13
                ),
                Achievement(
                    name='Detective',
                    description='Completar 50 ejercicios de identificación',
                    icon='bi-search',
                    category='tipo',
                    exercises_required=50,
                    reward_points=150,
                    reward_stars=15,
                    badge_color='silver',
                    order=14
                ),
                Achievement(
                    name='Centenario',
                    description='Completar 100 ejercicios totales',
                    icon='bi-100',
                    category='ejercicios',
                    exercises_required=100,
                    reward_points=200,
                    reward_stars=20,
                    badge_color='gold',
                    order=15
                )
            ]
            db.session.add_all(achievements)
            db.session.commit()
        
        return jsonify({'status': 'Base de datos inicializada'})
    
    return jsonify({'error': 'No autorizado'}), 403

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# ============================================
# EJECUCIÓN
# ============================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Verificar si hay logros, si no, inicializar
        if Achievement.query.count() == 0:
            print("Inicializando logros...")
            achievements = [
                Achievement(
                    name='Primeros Pasos',
                    description='Completar 10 ejercicios correctamente',
                    icon='bi-star',
                    category='ejercicios',
                    exercises_required=10,
                    reward_points=50,
                    reward_stars=5,
                    badge_color='bronze',
                    order=1
                ),
                Achievement(
                    name='Aprendiz',
                    description='Alcanzar 100 puntos',
                    icon='bi-book',
                    category='puntos',
                    points_required=100,
                    reward_points=100,
                    reward_stars=10,
                    badge_color='bronze',
                    order=2
                ),
                Achievement(
                    name='Comunicador',
                    description='Alcanzar 250 puntos',
                    icon='bi-chat',
                    category='puntos',
                    points_required=250,
                    reward_points=150,
                    reward_stars=15,
                    badge_color='silver',
                    order=3
                ),
                Achievement(
                    name='Experto',
                    description='Alcanzar 500 puntos',
                    icon='bi-trophy',
                    category='puntos',
                    points_required=500,
                    reward_points=200,
                    reward_stars=20,
                    badge_color='gold',
                    order=4
                )
            ]
            db.session.add_all(achievements)
            db.session.commit()
            print("Logros inicializados.")
    
    app.run(debug=True)
