from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

# Modelo de Usuario
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default='default.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    language = db.Column(db.String(10), default='es')
    
    # Estadísticas del usuario
    total_score = db.Column(db.Integer, default=0)
    total_stars = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)
    max_streak = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    experience_points = db.Column(db.Integer, default=0)
    
    # Relaciones
    progress = db.relationship('Progress', backref='user', lazy=True, uselist=False, cascade='all, delete-orphan')
    exercises_completed = db.relationship('CompletedExercise', backref='user', lazy=True, cascade='all, delete-orphan')
    custom_exercises = db.relationship('CustomExercise', backref='user', lazy=True, cascade='all, delete-orphan')
    flashcards_studied = db.relationship('FlashcardStudy', backref='user', lazy=True, cascade='all, delete-orphan')
    achievements_unlocked = db.relationship('UserAchievement', backref='user', lazy=True, cascade='all, delete-orphan')
    daily_goals = db.relationship('DailyGoal', backref='user', lazy=True, cascade='all, delete-orphan')
    practice_sessions = db.relationship('PracticeSession', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def get_rank(self):
        """Calcular ranking global del usuario"""
        users = User.query.order_by(User.total_score.desc()).all()
        for i, user in enumerate(users, 1):
            if user.id == self.id:
                return i
        return 0
    
    def get_level_progress(self):
        """Calcular progreso hacia el siguiente nivel"""
        exp_needed = self.level * 100
        return min(100, int((self.experience_points / exp_needed) * 100))
    
    def add_experience(self, points):
        """Añadir puntos de experiencia y actualizar nivel"""
        self.experience_points += points
        while self.experience_points >= self.level * 100:
            self.experience_points -= self.level * 100
            self.level += 1
        return self.level

# Modelo de Progreso
class Progress(db.Model):
    __tablename__ = 'progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Ejercicios
    exercises_total = db.Column(db.Integer, default=0)
    exercises_correct = db.Column(db.Integer, default=0)
    exercises_attempted = db.Column(db.Integer, default=0)
    
    # Por tipo de ejercicio
    transformacion_attempts = db.Column(db.Integer, default=0)
    transformacion_correct = db.Column(db.Integer, default=0)
    completar_attempts = db.Column(db.Integer, default=0)
    completar_correct = db.Column(db.Integer, default=0)
    identificar_attempts = db.Column(db.Integer, default=0)
    identificar_correct = db.Column(db.Integer, default=0)
    
    # Flashcards
    flashcards_studied = db.Column(db.Integer, default=0)
    flashcards_mastered = db.Column(db.Integer, default=0)
    
    # Práctica
    practice_sessions = db.Column(db.Integer, default=0)
    practice_time = db.Column(db.Integer, default=0)  # en minutos
    total_time_spent = db.Column(db.Integer, default=0)  # en segundos
    
    # Metas
    daily_goal = db.Column(db.Integer, default=10)
    weekly_goal = db.Column(db.Integer, default=50)
    monthly_goal = db.Column(db.Integer, default=200)
    
    # Estadísticas por categoría (almacenado como JSON)
    category_stats = db.Column(db.Text, default='{}')
    
    # Historial
    last_practice = db.Column(db.DateTime)
    last_achievement_check = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_accuracy(self):
        """Calcular porcentaje de aciertos"""
        if self.exercises_attempted == 0:
            return 0
        return round((self.exercises_correct / self.exercises_attempted) * 100, 1)
    
    def get_type_accuracy(self, exercise_type):
        """Calcular precisión por tipo de ejercicio"""
        attempts = getattr(self, f"{exercise_type}_attempts", 0)
        correct = getattr(self, f"{exercise_type}_correct", 0)
        if attempts == 0:
            return 0
        return round((correct / attempts) * 100, 1)
    
    def update_category_stats(self, category, correct):
        """Actualizar estadísticas por categoría"""
        stats = json.loads(self.category_stats)
        if category not in stats:
            stats[category] = {'total': 0, 'correct': 0}
        stats[category]['total'] += 1
        if correct:
            stats[category]['correct'] += 1
        self.category_stats = json.dumps(stats)
    
    def get_category_stats(self):
        """Obtener estadísticas por categoría"""
        return json.loads(self.category_stats)

# Modelo de Ejercicios Completados
class CompletedExercise(db.Model):
    __tablename__ = 'completed_exercises'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exercise_id = db.Column(db.Integer, nullable=False)
    exercise_type = db.Column(db.String(50))
    exercise_category = db.Column(db.String(50))
    exercise_difficulty = db.Column(db.String(20))
    
    # Resultados
    correct = db.Column(db.Boolean, default=False)
    points_earned = db.Column(db.Integer, default=0)
    stars_earned = db.Column(db.Integer, default=0)
    time_spent = db.Column(db.Integer, default=0)  # segundos
    attempts = db.Column(db.Integer, default=1)
    
    # Metadata
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    
    # Feedback del usuario (opcional)
    user_rating = db.Column(db.Integer)  # 1-5 estrellas de satisfacción
    user_comment = db.Column(db.Text)

# Modelo de Ejercicios Personalizados
class CustomExercise(db.Model):
    __tablename__ = 'custom_exercises'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Datos del ejercicio
    type = db.Column(db.String(50), nullable=False)  # transformacion, completar, identificar
    phrase = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    difficulty = db.Column(db.String(20), default='media')
    category = db.Column(db.String(50))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    times_used = db.Column(db.Integer, default=0)
    times_correct = db.Column(db.Integer, default=0)
    is_public = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    
    def get_success_rate(self):
        """Calcular tasa de éxito"""
        if self.times_used == 0:
            return 0
        return round((self.times_correct / self.times_used) * 100, 1)

# Modelo de Estudio de Flashcards
class FlashcardStudy(db.Model):
    __tablename__ = 'flashcard_study'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    flashcard_id = db.Column(db.Integer, nullable=False)
    flashcard_category = db.Column(db.String(50))
    
    # Progreso
    mastered = db.Column(db.Boolean, default=False)
    times_reviewed = db.Column(db.Integer, default=0)
    times_correct = db.Column(db.Integer, default=0)
    
    # Sistema de repaso espaciado
    last_reviewed = db.Column(db.DateTime)
    next_review = db.Column(db.DateTime)
    ease_factor = db.Column(db.Float, default=2.5)  # Factor de facilidad (algoritmo SM-2)
    interval = db.Column(db.Integer, default=1)  # Días hasta próximo repaso
    
    def update_review(self, quality):
        """Actualizar programación de repaso (algoritmo SM-2 modificado)"""
        if quality >= 3:  # Respuesta correcta
            if self.times_reviewed == 0:
                self.interval = 1
            elif self.times_reviewed == 1:
                self.interval = 6
            else:
                self.interval = round(self.interval * self.ease_factor)
            
            self.ease_factor = self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            if self.ease_factor < 1.3:
                self.ease_factor = 1.3
        else:  # Respuesta incorrecta
            self.interval = 1
            self.ease_factor = max(1.3, self.ease_factor - 0.2)
        
        self.next_review = datetime.utcnow() + timedelta(days=self.interval)
        self.times_reviewed += 1
        if quality >= 3:
            self.times_correct += 1

# Modelo de Logros
class Achievement(db.Model):
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    icon = db.Column(db.String(50))
    category = db.Column(db.String(50))
    
    # Requisitos
    points_required = db.Column(db.Integer, default=0)
    exercises_required = db.Column(db.Integer, default=0)
    streak_required = db.Column(db.Integer, default=0)
    custom_exercises_required = db.Column(db.Integer, default=0)
    flashcards_mastered_required = db.Column(db.Integer, default=0)
    
    # Recompensas
    reward_points = db.Column(db.Integer, default=50)
    reward_stars = db.Column(db.Integer, default=5)
    
    # Apariencia
    badge_color = db.Column(db.String(20), default='gold')
    badge_image = db.Column(db.String(200))
    hidden = db.Column(db.Boolean, default=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    order = db.Column(db.Integer, default=0)

# Modelo de Logros de Usuario
class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    notified = db.Column(db.Boolean, default=False)
    
    achievement = db.relationship('Achievement')

# Modelo de Metas Diarias
class DailyGoal(db.Model):
    __tablename__ = 'daily_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    
    # Progreso
    exercises_completed = db.Column(db.Integer, default=0)
    exercises_correct = db.Column(db.Integer, default=0)
    time_spent = db.Column(db.Integer, default=0)  # minutos
    stars_earned = db.Column(db.Integer, default=0)
    points_earned = db.Column(db.Integer, default=0)
    
    # Metas
    goal_achieved = db.Column(db.Boolean, default=False)
    goal_exceeded = db.Column(db.Boolean, default=False)
    
    # Bonus
    streak_bonus = db.Column(db.Integer, default=0)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='unique_daily_goal'),)

# Modelo de Sesiones de Práctica
class PracticeSession(db.Model):
    __tablename__ = 'practice_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    
    # Estadísticas de la sesión
    exercises_completed = db.Column(db.Integer, default=0)
    exercises_correct = db.Column(db.Integer, default=0)
    total_time = db.Column(db.Integer, default=0)  # segundos
    points_earned = db.Column(db.Integer, default=0)
    stars_earned = db.Column(db.Integer, default=0)
    
    # Tipos de ejercicios en la sesión
    exercise_types = db.Column(db.Text, default='[]')  # JSON array
    
    def end_session(self):
        """Finalizar sesión y calcular tiempo total"""
        self.ended_at = datetime.utcnow()
        if self.started_at:
            delta = self.ended_at - self.started_at
            self.total_time = int(delta.total_seconds())
        return self.total_time

# Modelo de Comentarios y Feedback
class ExerciseFeedback(db.Model):
    __tablename__ = 'exercise_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exercise_id = db.Column(db.Integer, nullable=False)
    exercise_type = db.Column(db.String(50))
    
    rating = db.Column(db.Integer)  # 1-5
    comment = db.Column(db.Text)
    helpful = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Modelo de Notificaciones
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    type = db.Column(db.String(50))  # achievement, goal, streak, etc.
    title = db.Column(db.String(100))
    message = db.Column(db.Text)
    icon = db.Column(db.String(50))
    color = db.Column(db.String(20))
    
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Acción asociada (opcional)
    action_url = db.Column(db.String(200))
    action_text = db.Column(db.String(50))

# Modelo de Estadísticas Semanales/Mensuales
class UserStatistics(db.Model):
    __tablename__ = 'user_statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    period = db.Column(db.String(20))  # weekly, monthly, yearly
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    # Estadísticas
    exercises_done = db.Column(db.Integer, default=0)
    exercises_correct = db.Column(db.Integer, default=0)
    time_spent = db.Column(db.Integer, default=0)
    points_earned = db.Column(db.Integer, default=0)
    stars_earned = db.Column(db.Integer, default=0)
    achievements_unlocked = db.Column(db.Integer, default=0)
    
    # Datos adicionales (JSON)
    extra_data = db.Column(db.Text, default='{}')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'period', 'start_date', name='unique_period'),)

# Modelo de Amigos/Seguidores (opcional para features sociales)
class UserFollow(db.Model):
    __tablename__ = 'user_follows'
    
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id', name='unique_follow'),)

# Modelo de Desafíos (opcional)
class Challenge(db.Model):
    __tablename__ = 'challenges'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    difficulty = db.Column(db.String(20))
    
    # Requisitos
    exercises_required = db.Column(db.Integer)
    days_required = db.Column(db.Integer)
    category_required = db.Column(db.String(50))
    
    # Recompensas
    reward_points = db.Column(db.Integer)
    reward_stars = db.Column(db.Integer)
    reward_achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'))
    
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)

# Modelo de Progreso en Desafíos
class UserChallenge(db.Model):
    __tablename__ = 'user_challenges'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    
    progress = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    challenge = db.relationship('Challenge')
