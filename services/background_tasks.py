"""
Background Task Manager
Coordinates all background processes and scheduled tasks using eventlet.
"""

import logging
import eventlet
from datetime import datetime, timedelta

from database.manager import DatabaseManager
from config.settings import config

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """Manages all background tasks and scheduled operations in a non-blocking way."""

    def __init__(self, socketio):
        self.name = "BackgroundTaskManager"
        self.db_manager = DatabaseManager()
        self.socketio = socketio
        self._tasks = []
        
        self._setup_scheduled_tasks()
        logger.info("BackgroundTaskManager initialized for eventlet.")

    def run(self):
        """The main scheduler loop, designed to be run as a green thread."""
        logger.info("Background task scheduler started.")
        while True:
            now = datetime.now()
            for task in self._tasks:
                if task['next_run'] <= now:
                    try:
                        logger.info(f"Spawning background task: {task['name']}")
                        eventlet.spawn(self._execute_task, task)
                    except Exception as e:
                        logger.error(f"Error spawning task {task['name']}: {e}", exc_info=True)

                    # Schedule the next run
                    task['last_run'] = now
                    task['next_run'] = now + timedelta(seconds=task['interval'])
            
            eventlet.sleep(1)  # Check for tasks to run every second

    def _setup_scheduled_tasks(self):
        """Sets up the default scheduled tasks."""
        self.register_task(
            name="data_cleanup",
            task_func=self._data_cleanup_task,
            interval_seconds=24 * 60 * 60  # Every 24 hours
        )
        self.register_task(
            name="system_stats_update",
            task_func=self._system_stats_task,
            interval_seconds=60 * 60  # Every hour
        )
        self.register_task(
            name="health_model_retrain",
            task_func=self._health_model_retrain_task,
            interval_seconds=7 * 24 * 60 * 60  # Every 7 days
        )
        logger.info(f"{len(self._tasks)} default scheduled tasks configured.")

    def register_task(self, name: str, task_func: callable, interval_seconds: int):
        """
        Registers a new task for the scheduler.
        """
        self._tasks.append({
            'name': name,
            'func': task_func,
            'interval': interval_seconds,
            'last_run': None,
            'next_run': datetime.now() + timedelta(seconds=interval_seconds)
        })

    def _execute_task(self, task: dict):
        """
        Executes a task with logging and error handling.
        """
        task_name = task['name']
        logger.info(f"Executing background task: {task_name}")
        
        try:
            start_time = datetime.now()
            result = task['func']()
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Task {task_name} completed in {duration:.2f}s.")
            
            self.db_manager.log_system_event(
                event_type='Scheduled_Task_Success',
                component='BackgroundTasks',
                message=f"Task '{task_name}' completed successfully.",
                details=f"Duration: {duration:.2f}s. Result: {result}",
                severity='INFO'
            )
        except Exception as e:
            logger.error(f"Error executing task {task_name}: {e}", exc_info=True)
            self.db_manager.log_system_event(
                event_type='Scheduled_Task_Failure',
                component='BackgroundTasks',
                message=f"Task '{task_name}' failed.",
                details=str(e),
                severity='ERROR'
            )

    # --- Task Implementations ---

    def _data_cleanup_task(self):
        """Cleans up old data from the database."""
        days_to_retain = config.data_retention_days
        cleanup_stats = self.db_manager.cleanup_old_data(days=days_to_retain)
        logger.info(f"Data cleanup task finished. Stats: {cleanup_stats}")
        return cleanup_stats

    def _system_stats_task(self):
        """Gathers and logs system-wide statistics."""
        stats = self.db_manager.get_system_statistics()
        self.socketio.emit('system_stats_update', stats)
        logger.info(f"System statistics task finished. Current health: {stats.get('current_health_score')}")
        return stats

    def _health_model_retrain_task(self):
        """Periodically retrains the AI models, if available."""
        logger.info("Attempting to run health model retraining task...")
        try:
            from ai.anomaly_detector import SKLEARN_AVAILABLE
            if not SKLEARN_AVAILABLE:
                logger.info("Skipping model retraining: scikit-learn dependency not installed.")
                return {"status": "skipped", "reason": "scikit-learn not installed"}
        except ImportError:
            logger.info("Skipping model retraining: Anomaly detector could not be imported.")
            return {"status": "skipped", "reason": "ImportError"}

        # This is a placeholder for a potentially long-running task.
        # In a real scenario, this might be offloaded to a separate worker process.
        logger.info("Starting health model retraining task...")
        # Placeholder for model retraining logic
        eventlet.sleep(300) # Simulate a long process
        logger.info("Health model retraining task finished.")
        return {"status": "success", "models_updated": ["anomaly_detector"]}
