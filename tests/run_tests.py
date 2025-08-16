#!/usr/bin/env python3
"""
测试运行脚本
提供不同级别的测试选项
"""
import argparse
import os
import sys
import subprocess
import logging
import glob

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def run_unit_tests(verbose=False):
    """运行单元测试（Mock测试）"""
    print("🧪 Running Unit Tests (Mock API calls)...")
    
    test_modules = [
        "tests.test_balance_algorithm_mocked",
        "tests.test_client_interface_mocked",
        "tests.test_output_validation"
    ]
    
    success = True
    for test_module in test_modules:
        test_file = test_module.replace(".", "/") + ".py"
        if os.path.exists(test_file):
            print(f"\n📝 Running {test_module}...")
            if verbose:
                # Run with real-time output for debugging
                result = subprocess.run([sys.executable, "-m", "unittest", test_module, "-v"])
                success = success and (result.returncode == 0)
            else:
                result = subprocess.run([sys.executable, "-m", "unittest", test_module], 
                                      capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"❌ {test_module} FAILED")
                    print("STDOUT:", result.stdout)
                    print("STDERR:", result.stderr)
                    success = False
                else:
                    print(f"✅ {test_module} PASSED")
        else:
            print(f"⚠️  {test_file} not found, skipping...")
    
    return success


def run_validation_tests():
    """运行输出验证测试"""
    print("🔍 Running Output Validation Tests...")
    
    test_modules = [
        "tests.test_output_validation"
    ]
    
    success = True
    for test_module in test_modules:
        test_file = test_module.replace(".", "/") + ".py"
        if os.path.exists(test_file):
            print(f"\n📝 Running {test_module}...")
            result = subprocess.run([sys.executable, "-m", "unittest", test_module, "-v"], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ {test_module} FAILED")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                success = False
            else:
                print(f"✅ {test_module} PASSED")
        else:
            print(f"⚠️  {test_file} not found, skipping...")
    
    return success


def run_validation_integration_tests():
    """运行输出验证集成测试（需要真实API密钥）"""
    print("🔍 Running Output Validation Integration Tests (Real API calls)...")
    
    if not os.getenv("SILICONFLOW_API_KEY"):
        print("⚠️  No SILICONFLOW_API_KEY found. Validation integration tests will be skipped.")
        return True
    
    test_file = "tests/test_validation_integration.py"
    
    if os.path.exists(test_file):
        print(f"\n📝 Running {test_file}...")
        result = subprocess.run([sys.executable, test_file],
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ {test_file} FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
        else:
            print(f"✅ {test_file} PASSED")
            return True
    else:
        print(f"⚠️  {test_file} not found, skipping...")
        return True


def run_integration_tests():
    """运行集成测试（需要真实API密钥）"""
    print("🔗 Running Integration Tests (Real API calls)...")
    
    if not os.getenv("SILICONFLOW_API_KEY"):
        print("⚠️  No SILICONFLOW_API_KEY found. Integration tests will be skipped.")
        return True
    
    test_files = [
        "tests/manual_test.py",
        "tests/multi_key_test.py"
    ]
    
    success = True
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n📝 Running {test_file}...")
            result = subprocess.run([sys.executable, "-m", "unittest", test_file],
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ {test_file} FAILED")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                success = False
            else:
                print(f"✅ {test_file} PASSED")
        else:
            print(f"⚠️  {test_file} not found, skipping...")
    
    return success


def run_provider_tests():
    """运行所有Provider测试（需要--provider参数）"""
    print("🏢 Running Provider Tests (Mock API calls for all providers)...")
    
    provider_test_files = glob.glob("tests/provider_tests/test_*_provider.py")
    
    if not provider_test_files:
        print("⚠️  No provider test files found in tests/provider_tests/")
        return True
    
    success = True
    for test_file in provider_test_files:
        print(f"\n📝 Running {test_file}...")
        result = subprocess.run([sys.executable, "-m", "unittest", test_file], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ {test_file} FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            success = False
        else:
            print(f"✅ {test_file} PASSED")
    
    return success


def run_provider_specific_tests(provider_name):
    """运行特定提供商的测试"""
    print(f"🏢 Running tests for {provider_name} provider...")
    
    test_file = f"tests/provider_tests/test_{provider_name}_provider.py"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file {test_file} not found!")
        return False
    
    result = subprocess.run([sys.executable, "-m", "unittest", test_file],
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ {provider_name} provider tests FAILED")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return False
    else:
        print(f"✅ {provider_name} provider tests PASSED")
        return True


def run_all_tests():
    """运行所有测试"""
    print("🚀 Running ALL tests...")
    
    unit_success = run_unit_tests()
    validation_success = run_validation_tests()
    integration_success = run_integration_tests()
    validation_integration_success = run_validation_integration_tests()
    
    if unit_success and validation_success and integration_success and validation_integration_success:
        print("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        print("\n💥 SOME TESTS FAILED!")
        return False


def main():
    parser = argparse.ArgumentParser(description="PLLM Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--validation", action="store_true", help="Run output validation tests only")
    parser.add_argument("--validation-integration", action="store_true", help="Run validation integration tests only")
    parser.add_argument("--provider", type=str, nargs='?', const='all', help="Run provider tests (specify provider name or 'all')")
    parser.add_argument("--all", action="store_true", help="Run all tests (unit + validation + integration)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    success = True
    
    if args.unit:
        success = run_unit_tests(args.verbose)
    elif args.integration:
        success = run_integration_tests()
    elif args.validation:
        success = run_validation_tests()
    elif args.validation_integration:
        success = run_validation_integration_tests()
    elif args.provider:
        if args.provider == 'all':
            success = run_provider_tests()
        else:
            success = run_provider_specific_tests(args.provider)
    elif args.all:
        success = run_all_tests()
    else:
        # 默认运行单元测试
        print("No specific test type specified, running unit tests by default...")
        print("Use --help to see all options")
        success = run_unit_tests(args.verbose)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()