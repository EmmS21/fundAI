import os
import sys
import logging
import subprocess
from datetime import datetime

# Set up logging with more verbose error reporting
log_dir = os.path.expanduser('~/.examiner/logs')
os.makedirs(log_dir, exist_ok=True)

# Create log file with timestamp
log_file = os.path.join(log_dir, f'debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('ExaminerDebug')

def check_environment():
    """Check environment before running the app"""
    logger.info("Checking environment...")
    
    # Check database directory
    db_dir = os.path.expanduser('~/.examiner/data')
    if not os.path.exists(db_dir):
        logger.error(f"Database directory missing: {db_dir}")
        return False
    
    # Check permissions
    try:
        test_file = os.path.join(db_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info(f"Directory {db_dir} is writable")
    except Exception as e:
        logger.error(f"Permission error on {db_dir}: {e}")
        return False
    
    return True

def run_app():
    logger.info("Starting The Examiner in debug mode...")
    
    # Check environment first
    if not check_environment():
        logger.error("Environment check failed")
        return
    
    # Get the application path
    app_path = os.path.join(os.getcwd(), 'dist', 'Examiner.app', 'Contents', 'MacOS', 'Examiner')
    
    if not os.path.exists(app_path):
        logger.error(f"Application not found at: {app_path}")
        return
    
    try:
        # Set environment variables for debugging
        env = os.environ.copy()
        env['EXAMINER_DEBUG'] = '1'
        env['PYTHONUNBUFFERED'] = '1'
        env['SQLALCHEMY_ECHO'] = 'True'
        env['PYTHONPATH'] = os.getcwd()  # Add current directory to Python path
        
        logger.info(f"Running application from: {app_path}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"PYTHONPATH: {env.get('PYTHONPATH')}")
        
        # Run the application
        process = subprocess.Popen(
            [app_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Real-time output logging
        while True:
            output = process.stdout.readline()
            if output:
                logger.info(f"APP OUTPUT: {output.strip()}")
            error = process.stderr.readline()
            if error:
                logger.error(f"APP ERROR: {error.strip()}")
            
            if process.poll() is not None:
                break
        
        # Get any remaining output
        remaining_output, remaining_error = process.communicate()
        if remaining_output:
            logger.info(f"REMAINING OUTPUT:\n{remaining_output}")
        if remaining_error:
            logger.error(f"REMAINING ERROR:\n{remaining_error}")
        
        # Check exit code
        return_code = process.poll()
        if return_code != 0:
            logger.error(f"Application failed with exit code: {return_code}")
            
            # Try to find any error logs in the application directory
            app_log_dir = os.path.expanduser('~/.examiner/logs')
            if os.path.exists(app_log_dir):
                logger.info("Checking application logs...")
                for log_file in os.listdir(app_log_dir):
                    if log_file.endswith('.log'):
                        with open(os.path.join(app_log_dir, log_file)) as f:
                            logger.info(f"Contents of {log_file}:\n{f.read()}")
            
    except Exception as e:
        logger.exception(f"Error running application: {e}")

if __name__ == "__main__":
    run_app()
