from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
import structlog

from app.models.user import User
from app.models.document import ReferenceDocument
from app.models.document import PlagiarismDocument
from app.models.plagiarism import PlagiarismCheck
from app.models.plan import SystemStats
from app.core.exceptions import NotFoundException

logger = structlog.get_logger(__name__)


class AdminService:
    """Service for admin operations and statistics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        # User statistics
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.status == "active").count()
        admin_users = self.db.query(User).filter(User.role == "admin").count()
        
        # Document statistics
        total_plagiarism_documents = self.db.query(PlagiarismDocument).count()
        total_reference_documents = self.db.query(ReferenceDocument).count()
        
        # Plagiarism check statistics
        total_checks = self.db.query(PlagiarismCheck).count()
        completed_checks = self.db.query(PlagiarismCheck).filter(PlagiarismCheck.check_status == "completed").count()
        failed_checks = self.db.query(PlagiarismCheck).filter(PlagiarismCheck.check_status == "failed").count()
        
        # Average similarity score
        avg_similarity = self.db.query(func.avg(PlagiarismCheck.total_similarity_score)).filter(
            PlagiarismCheck.check_status == "completed"
        ).scalar() or 0.0
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        recent_users = self.db.query(User).filter(User.created_at >= thirty_days_ago).count()
        recent_checks = self.db.query(PlagiarismCheck).filter(PlagiarismCheck.created_at >= thirty_days_ago).count()
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "admins": admin_users,
                "recent_registrations": recent_users
            },
            "documents": {
                "plagiarism_documents": total_plagiarism_documents,
                "reference_documents": total_reference_documents
            },
            "plagiarism_checks": {
                "total": total_checks,
                "completed": completed_checks,
                "failed": failed_checks,
                "recent": recent_checks,
                "average_similarity": round(avg_similarity, 2)
            },
            "generated_at": datetime.utcnow()
        }
    
    def get_user_activity_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get user activity statistics over time."""
        cutoff_date = datetime.utcnow().date() - timedelta(days=days)
        
        # Daily user registrations
        daily_registrations = self.db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.created_at >= cutoff_date
        ).group_by(func.date(User.created_at)).all()
        
        # Daily plagiarism checks
        daily_checks = self.db.query(
            func.date(PlagiarismCheck.created_at).label('date'),
            func.count(PlagiarismCheck.id).label('count')
        ).filter(
            PlagiarismCheck.created_at >= cutoff_date
        ).group_by(func.date(PlagiarismCheck.created_at)).all()
        
        # Combine data
        activity_data = {}
        
        for reg in daily_registrations:
            activity_data[reg.date] = {
                'date': reg.date,
                'registrations': reg.count,
                'checks': 0
            }
        
        for check in daily_checks:
            if check.date in activity_data:
                activity_data[check.date]['checks'] = check.count
            else:
                activity_data[check.date] = {
                    'date': check.date,
                    'registrations': 0,
                    'checks': check.count
                }
        
        return list(activity_data.values())
    
    def get_top_users_by_checks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by number of plagiarism checks."""
        top_users = self.db.query(
            User.id,
            User.username,
            User.full_name,
            func.count(PlagiarismCheck.id).label('check_count')
        ).join(
            PlagiarismCheck, User.id == PlagiarismCheck.user_id
        ).group_by(
            User.id, User.username, User.full_name
        ).order_by(
            func.count(PlagiarismCheck.id).desc()
        ).limit(limit).all()
        
        return [
            {
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'check_count': user.check_count
            }
            for user in top_users
        ]
    
    def get_similarity_distribution(self) -> Dict[str, int]:
        """Get distribution of similarity scores."""
        completed_checks = self.db.query(PlagiarismCheck).filter(
            PlagiarismCheck.check_status == "completed"
        ).all()
        
        distribution = {
            "0-10%": 0,
            "11-25%": 0,
            "26-50%": 0,
            "51-75%": 0,
            "76-90%": 0,
            "91-100%": 0
        }
        
        for check in completed_checks:
            score = check.total_similarity_score
            if score <= 10:
                distribution["0-10%"] += 1
            elif score <= 25:
                distribution["11-25%"] += 1
            elif score <= 50:
                distribution["26-50%"] += 1
            elif score <= 75:
                distribution["51-75%"] += 1
            elif score <= 90:
                distribution["76-90%"] += 1
            else:
                distribution["91-100%"] += 1
        
        return distribution
    
    def update_daily_stats(self, target_date: date = None) -> SystemStats:
        """Update daily system statistics."""
        if target_date is None:
            target_date = datetime.utcnow().date()
        
        # Check if stats already exist for this date
        existing_stats = self.db.query(SystemStats).filter(SystemStats.date == target_date).first()
        
        # Calculate statistics
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.status == "active").count()
        total_plagiarism_documents = self.db.query(PlagiarismDocument).count()
        total_reference_documents = self.db.query(ReferenceDocument).count()
        total_checks = self.db.query(PlagiarismCheck).count()
        
        avg_similarity = self.db.query(func.avg(PlagiarismCheck.total_similarity_score)).filter(
            PlagiarismCheck.check_status == "completed"
        ).scalar() or 0.0
        
        if existing_stats:
            # Update existing stats
            existing_stats.total_users = total_users
            existing_stats.active_users = active_users
            existing_stats.total_user_documents = total_plagiarism_documents  # Field name kept for DB compatibility
            existing_stats.total_reference_documents = total_reference_documents
            existing_stats.total_checks = total_checks
            existing_stats.average_similarity = round(avg_similarity, 2)
            
            self.db.commit()
            self.db.refresh(existing_stats)
            
            logger.info("Daily stats updated", date=target_date)
            return existing_stats
        else:
            # Create new stats
            stats = SystemStats(
                date=target_date,
                total_users=total_users,
                active_users=active_users,
                total_user_documents=total_plagiarism_documents,  # Field name kept for DB compatibility
                total_reference_documents=total_reference_documents,
                total_checks=total_checks,
                average_similarity=round(avg_similarity, 2)
            )
            
            self.db.add(stats)
            self.db.commit()
            self.db.refresh(stats)
            
            logger.info("Daily stats created", date=target_date)
            return stats
    
    def get_historical_stats(self, days: int = 30) -> List[SystemStats]:
        """Get historical system statistics."""
        cutoff_date = datetime.utcnow().date() - timedelta(days=days)
        
        return self.db.query(SystemStats).filter(
            SystemStats.date >= cutoff_date
        ).order_by(SystemStats.date.desc()).all()
    
    # Legacy get_pending_document_summary method has been removed
