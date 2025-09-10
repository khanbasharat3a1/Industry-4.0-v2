"""
Test Runner for AI Motor Monitoring System
Run this file to execute all tests without pytest command line issues
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_tests():
    """Run all tests manually"""
    print("🧪 Running AI Motor Monitoring System Tests")
    print("=" * 50)
    
    # First install pytest if needed
    try:
        import pytest
        print("✅ pytest found - running tests...")
        
        # Run tests using pytest.main()
        exit_code = pytest.main([
            'tests/',
            '-v',
            '--tb=short',
            '--color=yes'
        ])
        
        return exit_code
        
    except ImportError:
        print("❌ pytest not found - installing...")
        
        # Try to install pytest
        import subprocess
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pytest'])
            print("✅ pytest installed successfully")
            
            # Import and run after installation
            import pytest
            exit_code = pytest.main([
                'tests/',
                '-v',
                '--tb=short'
            ])
            return exit_code
            
        except Exception as e:
            print(f"❌ Failed to install pytest: {e}")
            print("🔧 Running basic tests manually...")
            
            # Fallback to manual test execution
            return run_manual_tests()

def run_manual_tests():
    """Run tests manually without pytest (fallback)"""
    test_count = 0
    passed_count = 0
    failed_count = 0
    
    print("\n📋 Manual Test Execution")
    print("-" * 30)
    
    # Test 1: Import Tests
    try:
        print("🧪 Testing imports...")
        
        # Test main app import
        try:
            from main import app
            print("  ✅ Main app imports successfully")
            passed_count += 1
        except Exception as e:
            print(f"  ❌ Main app import failed: {e}")
            failed_count += 1
        test_count += 1
        
        # Test config import
        try:
            from config.settings import config
            print("  ✅ Config imports successfully")
            passed_count += 1
        except Exception as e:
            print(f"  ❌ Config import failed: {e}")
            failed_count += 1
        test_count += 1
        
        # Test utils import
        try:
            from utils.validators import validate_esp_data
            print("  ✅ Utils imports successfully")
            passed_count += 1
        except Exception as e:
            print(f"  ❌ Utils import failed: {e}")
            failed_count += 1
        test_count += 1
        
    except Exception as e:
        print(f"❌ Import test setup failed: {e}")
        failed_count += 1
    
    # Test 2: Basic Functionality
    try:
        print("\n🧪 Testing basic functionality...")
        
        # Test ESP data validation
        try:
            from utils.validators import validate_esp_data
            test_data = {
                'TYPE': 'ADU_TEXT',
                'VAL1': '6.25',
                'VAL2': '24.0'
            }
            result = validate_esp_data(test_data)
            if result:
                print("  ✅ ESP data validation works")
                passed_count += 1
            else:
                print("  ❌ ESP data validation failed")
                failed_count += 1
        except Exception as e:
            print(f"  ❌ ESP validation test failed: {e}")
            failed_count += 1
        test_count += 1
        
        # Test health analyzer
        try:
            from ai.health_analyzer import MotorHealthAnalyzer
            analyzer = MotorHealthAnalyzer()
            health_score = analyzer.calculate_overall_health({
                'esp_current': 6.25,
                'esp_voltage': 24.0,
                'plc_motor_temp': 40.0
            })
            if 0 <= health_score <= 100:
                print("  ✅ Health analyzer works")
                passed_count += 1
            else:
                print("  ❌ Health analyzer returned invalid score")
                failed_count += 1
        except Exception as e:
            print(f"  ❌ Health analyzer test failed: {e}")
            failed_count += 1
        test_count += 1
        
    except Exception as e:
        print(f"❌ Functionality test setup failed: {e}")
        failed_count += 1
    
    # Test 3: API Endpoints (if Flask app available)
    try:
        print("\n🧪 Testing API endpoints...")
        
        from main import app
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            if response.status_code == 200:
                print("  ✅ Health endpoint works")
                passed_count += 1
            else:
                print(f"  ❌ Health endpoint failed: {response.status_code}")
                failed_count += 1
            test_count += 1
            
            # Test dashboard
            response = client.get('/')
            if response.status_code == 200:
                print("  ✅ Dashboard endpoint works")
                passed_count += 1
            else:
                print(f"  ❌ Dashboard endpoint failed: {response.status_code}")
                failed_count += 1
            test_count += 1
            
    except Exception as e:
        print(f"  ❌ API test setup failed: {e}")
        failed_count += 1
    
    # Print results
    print(f"\n📊 Test Results")
    print(f"Total Tests: {test_count}")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"Success Rate: {(passed_count/test_count*100):.1f}%")
    
    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    print("🔧 AI Motor Monitoring System - Test Runner")
    print("🎯 This will test your system components")
    print()
    
    exit_code = run_tests()
    
    if exit_code == 0:
        print("\n🎉 All tests passed! Your system is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
    
    print(f"\nExit code: {exit_code}")
    sys.exit(exit_code)
