import json
import random
import hashlib
from datetime import datetime, timedelta
from models import db, User, Progress, CompletedExercise, CustomExercise, FlashcardStudy, Achievement, UserAchievement, DailyGoal, PracticeSession, Notification

# ============================================
# FUNCIONES DE CARGA DE DATOS
# ============================================

def load_exercises():
    """Cargar ejercicios desde el archivo JSON"""
    try:
        with open('data/ejercicios.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('ejercicios', [])
    except FileNotFoundError:
        print("Error: Archivo data/ejercicios.json no encontrado")
        return []
    except json.JSONDecodeError:
        print("Error: Archivo data/ejercicios.json con formato inválido")
        return []

def load_flashcards():
    """Cargar flashcards desde el archivo JSON"""
    try:
        with open('data/flashcards.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('flashcards', [])
    except FileNotFoundError:
        print("Error: Archivo data/flashcards.json no encontrado")
        return []
    except json.JSONDecodeError:
        print("Error: Archivo data/flashcards.json con formato inválido")
        return []

# ============================================
# FUNCIONES DE EJERCICIOS
# ============================================

def get_random_exercise(exercise_type=None, difficulty=None, category=None, exclude_ids=None):
    """Obtener ejercicio aleatorio con filtros opcionales"""
    exercises = load_exercises()
    
    if exercise_type:
        exercises = [e for e in exercises if e.get('tipo') == exercise_type]
    if difficulty:
        exercises = [e for e in exercises if e.get('dificultad') == difficulty]
    if category:
        exercises = [e for e in exercises if e.get('categoria') == category]
    if exclude_ids:
        exercises = [e for e in exercises if e.get('id') not in exclude_ids]
    
    return random.choice(exercises) if exercises else None

def get_exercise_by_id(exercise_id):
    """Obtener un ejercicio específico por ID"""
    exercises = load_exercises()
    for exercise in exercises:
        if exercise.get('id') == exercise_id:
            return exercise
    return None

def get_exercises_by_category(category, limit=None):
    """Obtener ejercicios por categoría"""
    exercises = load_exercises()
    filtered = [e for e in exercises if e.get('categoria') == category]
    if limit:
        filtered = filtered[:limit]
    return filtered

def get_exercises_by_difficulty(difficulty, limit=None):
    """Obtener ejercicios por dificultad"""
    exercises = load_exercises()
    filtered = [e for e in exercises if e.get('dificultad') == difficulty]
    if limit:
        filtered = filtered[:limit]
    return filtered

def get_recommended_exercises(user, count=5):
    """Recomendar ejercicios basado en el rendimiento del usuario"""
    # Obtener IDs de ejercicios completados
    completed_ids = [ce.exercise_id for ce in CompletedExercise.query.filter_by(user_id=user.id).all()]
    
    # Obtener ejercicios no completados
    exercises = load_exercises()
    available = [e for e in exercises if e['id'] not in completed_ids]
    
    # Si hay pocos disponibles, incluir algunos ya vistos pero con bajo rendimiento
    if len(available) < count:
        # Obtener ejercicios con bajo rendimiento
        poor_performance = []
        for ex_id in completed_ids:
            attempts = CompletedExercise.query.filter_by(
                user_id=user.id, 
                exercise_id=ex_id
            ).count()
            correct = CompletedExercise.query.filter_by(
                user_id=user.id, 
                exercise_id=ex_id,
                correct=True
            ).count()
            if attempts > 0 and (correct / attempts) < 0.5:
                exercise = get_exercise_by_id(ex_id)
                if exercise:
                    poor_performance.append(exercise)
        
        available = exercises if not available else available + poor_performance
    
    # Priorizar según nivel del usuario
    if user.level < 3:
        available = [e for e in available if e.get('dificultad') == 'facil']
    elif user.level < 6:
        available = [e for e in available if e.get('dificultad') in ['facil', 'media']]
    
    # Seleccionar aleatoriamente
    return random.sample(available, min(count, len(available))) if available else []

# ============================================
# FUNCIONES DE FLASHCARDS
# ============================================

def get_random_flashcard(category=None, exclude_ids=None):
    """Obtener flashcard aleatoria con filtros"""
    flashcards = load_flashcards()
    
    if category:
        flashcards = [f for f in flashcards if f.get('categoria') == category]
    if exclude_ids:
        flashcards = [f for f in flashcards if f.get('id') not in exclude_ids]
    
    return random.choice(flashcards) if flashcards else None

def get_flashcard_by_id(flashcard_id):
    """Obtener una flashcard específica por ID"""
    flashcards = load_flashcards()
    for flashcard in flashcards:
        if flashcard.get('id') == flashcard_id:
            return flashcard
    return None

def get_due_flashcards(user, limit=10):
    """Obtener flashcards que deben ser repasadas (sistema de repaso espaciado)"""
    studies = FlashcardStudy.query.filter_by(
        user_id=user.id,
        mastered=False
    ).filter(
        FlashcardStudy.next_review <= datetime.utcnow()
    ).limit(limit).all()
    
    result = []
    for study in studies:
        flashcard = get_flashcard_by_id(study.flashcard_id)
        if flashcard:
            result.append({
                'study': study,
                'flashcard': flashcard
            })
    
    return result

# ============================================
# FUNCIONES DE CÁLCULO DE PUNTUACIÓN
# ============================================

def calculate_stars(points, time_spent, max_points, accuracy=100):
    """Calcular estrellas basado en rendimiento (1-5 estrellas)"""
    stars = 1  # Mínimo 1 estrella por completar
    
    # Por puntuación (máximo 3 estrellas base)
    if points >= max_points * 0.7:
        stars += 1
    if points >= max_points * 0.9:
        stars += 1
    if points >= max_points:
        stars += 1
    
    # Bonus por rapidez
    if time_spent < 30:  # menos de 30 segundos
        stars += 1
    
    # Bonus por precisión perfecta
    if accuracy == 100:
        stars += 1
    
    return min(stars, 5)  # Máximo 5 estrellas

def calculate_experience(points, stars, time_spent):
    """Calcular puntos de experiencia ganados"""
    base_exp = points * 2
    star_bonus = stars * 5
    time_bonus = max(0, 30 - time_spent)  # Bonus por rapidez
    
    return base_exp + star_bonus + time_bonus

# ============================================
# FUNCIONES DE LOGROS
# ============================================

def check_achievements(user):
    """Verificar y desbloquear logros para un usuario"""
    progress = user.progress
    if not progress:
        progress = Progress(user_id=user.id)
        db.session.add(progress)
        db.session.commit()
    
    # Contar ejercicios personalizados
    custom_count = CustomExercise.query.filter_by(user_id=user.id).count()
    
    # Contar flashcards dominadas
    mastered_flashcards = FlashcardStudy.query.filter_by(
        user_id=user.id,
        mastered=True
    ).count()
    
    achievements = Achievement.query.all()
    new_achievements = []
    
    for achievement in achievements:
        # Verificar si ya lo tiene
        existing = UserAchievement.query.filter_by(
            user_id=user.id, 
            achievement_id=achievement.id
        ).first()
        
        if existing:
            continue
        
        unlocked = False
        
        # Verificar condiciones
        if achievement.points_required > 0:
            if user.total_score >= achievement.points_required:
                unlocked = True
        
        elif achievement.exercises_required > 0:
            if progress.exercises_correct >= achievement.exercises_required:
                unlocked = True
        
        elif achievement.streak_required > 0:
            if user.current_streak >= achievement.streak_required:
                unlocked = True
        
        elif achievement.custom_exercises_required > 0:
            if custom_count >= achievement.custom_exercises_required:
                unlocked = True
        
        elif achievement.flashcards_mastered_required > 0:
            if mastered_flashcards >= achievement.flashcards_mastered_required:
                unlocked = True
        
        if unlocked:
            # Otorgar logro
            ua = UserAchievement(
                user_id=user.id,
                achievement_id=achievement.id
            )
            db.session.add(ua)
            new_achievements.append(achievement)
            
            # Otorgar recompensas
            user.total_score += achievement.reward_points
            user.total_stars += achievement.reward_stars
            
            # Crear notificación
            create_notification(
                user_id=user.id,
                type='achievement',
                title='¡Nuevo logro desbloqueado!',
                message=f"Has obtenido: {achievement.name}",
                icon=achievement.icon,
                color='success'
            )
    
    if new_achievements:
        db.session.commit()
    
    return new_achievements

# ============================================
# FUNCIONES DE RACHA (STREAK)
# ============================================

def update_streak(user):
    """Actualizar racha diaria del usuario"""
    today = datetime.utcnow().date()
    
    # Buscar si ya practicó hoy
    practiced_today = DailyGoal.query.filter_by(
        user_id=user.id,
        date=today
    ).first()
    
    yesterday = today - timedelta(days=1)
    practiced_yesterday = DailyGoal.query.filter_by(
        user_id=user.id,
        date=yesterday
    ).first()
    
    # Calcular nueva racha
    if practiced_today and practiced_today.exercises_completed > 0:
        if practiced_yesterday and practiced_yesterday.goal_achieved:
            user.current_streak += 1
        else:
            user.current_streak = 1
        
        if user.current_streak > user.max_streak:
            user.max_streak = user.current_streak
        
        # Bonus por racha
        if user.current_streak % 7 == 0:  # Cada semana
            bonus = user.current_streak * 10
            user.total_score += bonus
            create_notification(
                user_id=user.id,
                type='streak',
                title=f'¡Racha de {user.current_streak} días!',
                message=f'Has ganado {bonus} puntos de bonus',
                icon='bi-calendar-check',
                color='warning'
            )
    
    db.session.commit()
    return user.current_streak

# ============================================
# FUNCIONES DE NOTIFICACIONES
# ============================================

def create_notification(user_id, type, title, message, icon=None, color=None, action_url=None, action_text=None):
    """Crear una notificación para un usuario"""
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        icon=icon,
        color=color,
        action_url=action_url,
        action_text=action_text
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def get_unread_notifications(user_id, limit=10):
    """Obtener notificaciones no leídas"""
    return Notification.query.filter_by(
        user_id=user_id,
        read=False
    ).order_by(Notification.created_at.desc()).limit(limit).all()

def mark_notifications_as_read(user_id):
    """Marcar todas las notificaciones como leídas"""
    Notification.query.filter_by(user_id=user_id, read=False).update({'read': True})
    db.session.commit()

# ============================================
# FUNCIONES DE RANKING
# ============================================

def get_leaderboard(limit=10, by='score'):
    """Obtener ranking de usuarios"""
    if by == 'score':
        users = User.query.order_by(User.total_score.desc()).limit(limit).all()
    elif by == 'streak':
        users = User.query.order_by(User.max_streak.desc()).limit(limit).all()
    elif by == 'stars':
        users = User.query.order_by(User.total_stars.desc()).limit(limit).all()
    else:
        users = User.query.order_by(User.total_score.desc()).limit(limit).all()
    
    return [(i+1, user) for i, user in enumerate(users)]

def get_user_rank(user, by='score'):
    """Obtener la posición de un usuario en el ranking"""
    if by == 'score':
        users = User.query.order_by(User.total_score.desc()).all()
    else:
        users = User.query.order_by(User.total_score.desc()).all()
    
    for i, u in enumerate(users, 1):
        if u.id == user.id:
            return i
    return 0

# ============================================
# FUNCIONES DE ESTADÍSTICAS
# ============================================

def get_user_stats(user, days=30):
    """Obtener estadísticas detalladas del usuario"""
    since_date = datetime.utcnow() - timedelta(days=days)
    
    # Ejercicios en período
    exercises = CompletedExercise.query.filter(
        CompletedExercise.user_id == user.id,
        CompletedExercise.completed_at >= since_date
    ).all()
    
    # Metas diarias en período
    daily_goals = DailyGoal.query.filter(
        DailyGoal.user_id == user.id,
        DailyGoal.date >= since_date.date()
    ).all()
    
    # Estadísticas por día
    daily_stats = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        day_goals = [g for g in daily_goals if g.date == date]
        day_exercises = [e for e in exercises if e.completed_at.date() == date]
        
        daily_stats.append({
            'date': date.isoformat(),
            'exercises': len(day_exercises),
            'correct': len([e for e in day_exercises if e.correct]),
            'points': sum(e.points_earned for e in day_exercises),
            'stars': sum(e.stars_earned for e in day_exercises),
            'goal_achieved': any(g.goal_achieved for g in day_goals) if day_goals else False
        })
    
    # Estadísticas por tipo
    type_stats = {}
    for exercise in exercises:
        ex_type = exercise.exercise_type
        if ex_type not in type_stats:
            type_stats[ex_type] = {'total': 0, 'correct': 0}
        type_stats[ex_type]['total'] += 1
        if exercise.correct:
            type_stats[ex_type]['correct'] += 1
    
    # Estadísticas por categoría
    category_stats = {}
    for exercise in exercises:
        cat = exercise.exercise_category
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'correct': 0}
        category_stats[cat]['total'] += 1
        if exercise.correct:
            category_stats[cat]['correct'] += 1
    
    return {
        'daily': daily_stats,
        'by_type': type_stats,
        'by_category': category_stats,
        'total_exercises': len(exercises),
        'total_correct': len([e for e in exercises if e.correct]),
        'total_points': sum(e.points_earned for e in exercises),
        'total_stars': sum(e.stars_earned for e in exercises),
        'accuracy': (len([e for e in exercises if e.correct]) / len(exercises) * 100) if exercises else 0
    }

# ============================================
# FUNCIONES DE METAS DIARIAS
# ============================================

def update_daily_goal(user, exercises_completed=1, correct=True, points=0, stars=0, time_spent=0):
    """Actualizar la meta diaria del usuario"""
    today = datetime.utcnow().date()
    
    daily = DailyGoal.query.filter_by(
        user_id=user.id,
        date=today
    ).first()
    
    if not daily:
        daily = DailyGoal(
            user_id=user.id,
            date=today,
            exercises_completed=exercises_completed,
            exercises_correct=1 if correct else 0,
            points_earned=points,
            stars_earned=stars,
            time_spent=time_spent
        )
        db.session.add(daily)
    else:
        daily.exercises_completed += exercises_completed
        if correct:
            daily.exercises_correct += 1
        daily.points_earned += points
        daily.stars_earned += stars
        daily.time_spent += time_spent
    
    # Verificar si alcanzó la meta
    progress = user.progress
    if daily.exercises_completed >= progress.daily_goal and not daily.goal_achieved:
        daily.goal_achieved = True
        
        # Bonus por meta cumplida
        bonus = 50
        user.total_score += bonus
        
        # Verificar si excedió la meta
        if daily.exercises_completed >= progress.daily_goal * 1.5:
            daily.goal_exceeded = True
            bonus_extra = 25
            user.total_score += bonus_extra
        
        create_notification(
            user_id=user.id,
            type='goal',
            title='¡Meta diaria cumplida!',
            message=f'Has completado {daily.exercises_completed} ejercicios hoy. +{bonus} puntos',
            icon='bi-trophy',
            color='success'
        )
    
    db.session.commit()
    return daily

# ============================================
# FUNCIONES DE SESIONES DE PRÁCTICA
# ============================================

def start_practice_session(user):
    """Iniciar una nueva sesión de práctica"""
    session = PracticeSession(user_id=user.id)
    db.session.add(session)
    db.session.commit()
    return session

def end_practice_session(session_id):
    """Finalizar una sesión de práctica"""
    session = PracticeSession.query.get(session_id)
    if session:
        session.end_session()
        db.session.commit()
    return session

# ============================================
# FUNCIONES DE BÚSQUEDA Y FILTROS
# ============================================

def search_exercises(query, filters=None):
    """Buscar ejercicios por texto"""
    exercises = load_exercises()
    results = []
    
    query = query.lower()
    for exercise in exercises:
        if query in exercise.get('frase', '').lower() or query in exercise.get('respuesta', '').lower():
            # Aplicar filtros adicionales
            match = True
            if filters:
                if filters.get('tipo') and exercise.get('tipo') != filters['tipo']:
                    match = False
                if filters.get('dificultad') and exercise.get('dificultad') != filters['dificultad']:
                    match = False
                if filters.get('categoria') and exercise.get('categoria') != filters['categoria']:
                    match = False
            
            if match:
                results.append(exercise)
    
    return results

# ============================================
# FUNCIONES DE EXPORTACIÓN/IMPORTACIÓN
# ============================================

def export_user_data(user):
    """Exportar todos los datos de un usuario (para backup)"""
    data = {
        'user': {
            'username': user.username,
            'email': user.email,
            'total_score': user.total_score,
            'total_stars': user.total_stars,
            'level': user.level,
            'created_at': user.created_at.isoformat()
        },
        'progress': {
            'exercises_attempted': user.progress.exercises_attempted,
            'exercises_correct': user.progress.exercises_correct,
            'flashcards_studied': user.progress.flashcards_studied,
            'flashcards_mastered': user.progress.flashcards_mastered
        },
        'exercises': [],
        'achievements': [],
        'custom_exercises': []
    }
    
    # Ejercicios completados
    for ex in user.exercises_completed:
        data['exercises'].append({
            'exercise_id': ex.exercise_id,
            'correct': ex.correct,
            'points': ex.points_earned,
            'stars': ex.stars_earned,
            'date': ex.completed_at.isoformat()
        })
    
    # Logros
    for ua in user.achievements_unlocked:
        data['achievements'].append({
            'achievement_id': ua.achievement_id,
            'unlocked_at': ua.unlocked_at.isoformat()
        })
    
    # Ejercicios personalizados
    for ce in user.custom_exercises:
        data['custom_exercises'].append({
            'type': ce.type,
            'phrase': ce.phrase,
            'answer': ce.answer,
            'difficulty': ce.difficulty,
            'category': ce.category
        })
    
    return data

# ============================================
# FUNCIONES DE UTILIDAD GENERAL
# ============================================

def generate_avatar_name(username):
    """Generar un nombre de archivo para avatar basado en el username"""
    hash_obj = hashlib.md5(username.encode())
    return f"avatar_{hash_obj.hexdigest()[:10]}.png"

def format_time(seconds):
    """Formatear tiempo en segundos a formato legible"""
    if seconds < 60:
        return f"{seconds} segundos"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minutos"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def get_week_dates():
    """Obtener las fechas de la última semana"""
    today = datetime.utcnow().date()
    return [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

def get_month_dates():
    """Obtener las fechas del último mes"""
    today = datetime.utcnow().date()
    dates = []
    for i in range(30, -1, -1):
        dates.append((today - timedelta(days=i)).isoformat())
    return dates
