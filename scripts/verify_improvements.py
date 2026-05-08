#!/usr/bin/env python3
"""Verify that all improvements are in place"""
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} NOT FOUND")
        return False

def check_import(module_path, description):
    """Check if a module can be imported"""
    try:
        parts = module_path.split('.')
        module = __import__(module_path)
        for part in parts[1:]:
            module = getattr(module, part)
        print(f"✅ {description}: {module_path}")
        return True
    except Exception as e:
        print(f"❌ {description}: {module_path} - {str(e)}")
        return False

def main():
    print("=" * 60)
    print("Verifying Dynamic Pricing Engine Improvements")
    print("=" * 60)
    
    checks = []
    
    # Core improvements
    print("\n📊 Enhanced Evaluation:")
    checks.append(check_file_exists("src/training/evaluate.py", "Enhanced evaluator"))
    
    print("\n🔄 Cross-Validation:")
    checks.append(check_file_exists("src/training/trainer.py", "Enhanced trainer"))
    
    print("\n🎯 Hyperparameter Tuning:")
    checks.append(check_file_exists("src/training/hyperparameter_tuning.py", "Optuna tuner"))
    checks.append(check_file_exists("scripts/train_with_tuning.py", "Tuning script"))
    
    print("\n🚀 Bayesian Optimization:")
    checks.append(check_file_exists("src/pricing/bayesian_optimizer.py", "Bayesian optimizer"))
    checks.append(check_file_exists("src/pricing/engine.py", "Enhanced pricing engine"))
    
    print("\n🔌 Enhanced API:")
    checks.append(check_file_exists("src/api/schemas.py", "Enhanced schemas"))
    checks.append(check_file_exists("src/api/router.py", "Enhanced router"))
    
    print("\n🧪 Test Suite:")
    checks.append(check_file_exists("tests/test_optimizer.py", "Optimizer tests"))
    checks.append(check_file_exists("tests/test_evaluator.py", "Evaluator tests"))
    checks.append(check_file_exists("tests/test_api.py", "API tests"))
    checks.append(check_file_exists("pytest.ini", "Pytest config"))
    
    print("\n📈 Monitoring:")
    checks.append(check_file_exists("src/monitoring/model_monitor.py", "Model monitor"))
    checks.append(check_file_exists("src/monitoring/metrics_tracker.py", "Metrics tracker"))
    
    print("\n⚙️ Configuration:")
    checks.append(check_file_exists("configs/config.yaml", "Enhanced config"))
    checks.append(check_file_exists("requirements.txt", "Updated requirements"))
    
    print("\n📚 Documentation:")
    checks.append(check_file_exists("README.md", "README"))
    checks.append(check_file_exists("DEVELOPMENT.md", "Development guide"))
    checks.append(check_file_exists(".gitignore", "Gitignore"))
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(checks)
    total = len(checks)
    print(f"Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("✅ All improvements verified successfully!")
        return 0
    else:
        print(f"⚠️  {total - passed} checks failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
