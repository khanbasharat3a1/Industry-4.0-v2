"""
Background Task Manager
Coordinates all background processes and scheduled tasks
"""

import threading
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Callable
import schedule

from database.manager import DatabaseManager
from config.settings import config

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """Manages all background tasks and scheduled operations"""
    
    def __init__(self):
        self.name = "BackgroundTaskManager"
        self.db_manager = DatabaseManager()
        
        # Task control
        self._stop_event = threading.Event()
        self._running_tasks = {}
        self._task_threads = []
        
        # Task registry
        self._scheduled_tasks = []
        
        # Initialize scheduled tasks
        self._setup_scheduled_tasks()
    
    def start(self):
        """Start all background tasks"""
        try:
            logger.info("Starting background task manager...")
            
            # Start scheduler thread
            scheduler_thread = threading.Thread(target=self._scheduler_worker, daemon=True)
            scheduler_thread.start()
            self._task_threads.append(scheduler_thread)
            
            # Start task monitor thread
            monitor_thread = threading.Thread(target=self._task_monitor, daemon=True)
            monitor_thread.start()
            self._task_threads.append(monitor_thread)
            
            logger.info("Background task manager started successfully")
            
        except Exception as e:
            logger.error(f"Error starting background task manager: {e}")
            raise
    
    def stop(self):
        """Stop all background tasks"""
        logger.info("Stopping background task manager...")
        self._stop_event.set()
        
        # Wait for threads to finish
        for thread in self._task_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        logger.info("Background task manager stopped")
    
    def register_task(self, name: str, task_func: Callable, interval: str):
        """
        Register a new scheduled task
        
        Args:
            name: Task name
            task_func: Function to execute
            interval: Schedule interval (e.g., '5.minutes', '1.hour', '1.day')
        """
        try:
            # Parse interval and schedule
            if interval.endswith('.minutes'):
                minutes = int(interval.split('.')[0])
                schedule.every(minutes).minutes.do(self._execute_task, name, task_func)
            elif interval.endswith('.hours'):
                hours = int(interval.split('.')[0])
                schedule.every(hours).hours.do(self._execute_task, name, task_func)
            elif interval.endswith('.days'):
                days = int(interval.split('.')[0])
                schedule.every(days).days.do(self._execute_task, name, task_func)
            else:
                logger.error(f"Invalid interval format: {interval}")
                return
            
            self._scheduled_tasks.append({
                'name': name,
                'function': task_func,
                'interval': interval,
                'registered_at': datetime.now()
            })
            
            logger.info(f"Task registered: {name} - {interval}")
            
        except Exception as e:
            logger.error(f"Error registering task {name}: {e}")
    
    def _setup_scheduled_tasks(self):
        """Setup default scheduled tasks"""
        
        # Data cleanup task (daily)
        schedule.every().day.at("02:00").do(
            self._execute_task, 
            "data_cleanup", 
            self._data_cleanup_task
        )
        
        # System statistics update (hourly)
        schedule.every().hour.do(
            self._execute_task,
            "system_stats_update",
            self._system_stats_task
        )
        
        # Health model retraining (weekly)
        schedule.every().sunday.at("03:00").do(
            self._execute_task,
            "health_model_retrain",
            self._health_model_retrain_task
        )
        
        # Connection health check (every 5 minutes)
        schedule.every(5).minutes.do(
            self._execute_task,
            "connection_health_check",
            self._connection_health_check
        )
        
        logger.info("Default scheduled tasks configured")
    
    def _scheduler_worker(self):
        """Background scheduler worker"""
        logger.info("Scheduler worker started")
        
        while not self._stop_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in scheduler worker: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _task_monitor(self):
        """Monitor running tasks and log status"""
        while not self._stop_event.is_set():
            try:
                # Log task status every 10 minutes
                if datetime.now().minute % 10 == 0:
                    active_tasks = len(self._running_tasks)
                    total_tasks = len(self._scheduled_tasks)
                    
                    self.db_manager.log_system_event(
                        event_type='Task_Status',
                        component='BackgroundTasks',
                        message=f'Task status: {active_tasks} running, {total_tasks} total scheduled'
                    )
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in task monitor: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _execute_task(self, task_name: str, task_func: Callable):
        """Execute a scheduled task with error handling and logging"""
        if task_name in self._running_tasks:
            logger.warning(f"Task {task_name} is already running, skipping")
            return
        
        self._running_tasks[task_name] = {
            'started_at': datetime.now(),
            'status': 'running'
        }
        
        try:
            logger.info(f"Executing scheduled task: {task_name}")
            start_time = time.time()
            
            # Execute the task
            result = task_func()
            
            execution_time = time.time() - start_time
            
            # Log successful completion
            self.db_manager.log_system_event(
                event_type='Scheduled_Task',
                component='BackgroundTasks',
                message=f'Task {task_name} completed successfully',
                details=f'Execution time: {execution_time:.2f}s, Result: {result}'
            )
            
            logger.info(f"Task {task_name} completed in {execution_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error executing task {task_name}: {e}")
            
            # Log error
            self.db_manager.log_system_event(
                event_type='Task_Error',
                component='BackgroundTasks',
                message=f'Task {task_name} failed',
                severity='ERROR',
                details=str(e)
            )
            
        finally:
            # Remove from running tasks
            if task_name in self._running_tasks:
                del self._running_tasks[task_name]
    
    def _data_cleanup_task(self) -> Dict:
        """Cleanup old data"""
        try:
            cleanup_result = self.db_manager.cleanup_old_data()
            logger.info(f"Data cleanup completed: {cleanup_result}")
            return cleanup_result
        except Exception as e:
            logger.error(f"Data cleanup task failed: {e}")
            return {'error': str(e)}
    
    def _system_stats_task(self) -> Dict:
        """Update system statistics"""
        try:
            stats = self.db_manager.get_system_statistics()
            
            # Log key metrics
            self.db_manager.log_system_event(
                event_type='System_Stats',
                component='BackgroundTasks',
                message='System statistics updated',
                details=f"Health: {stats.get('current_health_score', 0)}%, "
                       f"Uptime: {stats.get('system_uptime_24h', 0)}%, "
                       f"Alerts: {stats.get('active_alerts', 0)}"
            )
            
            return {'status': 'success', 'stats': stats}
            
        except Exception as e:
            logger.error(f"System stats task failed: {e}")
            return {'error': str(e)}
    
    def _health_model_retrain_task(self) -> Dict:
        """Retrain health prediction models"""
        try:
            # Get training data (last 30 days)
            training_data = self.db_manager.get_recent_data_df(hours=24*30)
            
            if len(training_data) < 100:
                logger.warning("Insufficient data for model retraining")
                return {'status': 'skipped', 'reason': 'insufficient_data'}
            
            # Retrain anomaly detector
            from ai.anomaly_detector import MotorAnomalyDetector
            anomaly_detector = MotorAnomalyDetector()
            
            success = anomaly_detector.train_model(training_data)
            
            if success:
                logger.info("Health models retrained successfully")
                return {'status': 'success', 'training_samples': len(training_data)}
            else:
                logger.error("Health model retraining failed")
                return {'status': 'failed', 'reason': 'training_error'}
                
        except Exception as e:
            logger.error(f"Health model retrain task failed: {e}")
            return {'error': str(e)}
    
    def _connection_health_check(self) -> Dict:
        """Check connection health and log status"""
        try:
            # This would be called by the data processor
            # For now, just log that the check ran
            self.db_manager.log_system_event(
                event_type='Connection_Check',
                component='BackgroundTasks',
                message='Connection health check completed'
            )
            
            return {'status': 'success'}
            
        except Exception as e:
            logger.error(f"Connection health check failed: {e}")
            return {'error': str(e)}
    
    def get_task_status(self) -> Dict:
        """Get status of all tasks"""
        return {
            'running_tasks': dict(self._running_tasks),
            'scheduled_tasks': self._scheduled_tasks,
            'next_runs': [
                {
                    'task': job.tags[0] if job.tags else 'unknown',
                    'next_run': job.next_run.isoformat() if job.next_run else None
                }
                for job in schedule.jobs
            ]
        }
