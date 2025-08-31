#!/usr/bin/env python3
"""
GEE Templates Test Runner

Simple script to run GEE template tests with various options.
"""

import sys
import os
import argparse

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

def run_single_template_test(template_name: str):
    """Run test for a single template."""
    from test_all_gee_templates import GEEAllTemplatesTester
    
    tester = GEEAllTemplatesTester()
    
    if template_name not in tester.test_queries:
        print(f"❌ Template '{template_name}' not found!")
        print(f"Available templates: {list(tester.test_queries.keys())}")
        return None
    
    print(f"🧪 Testing single template: {template_name}")
    result = tester.test_single_template(template_name, tester.test_queries[template_name])
    return result

def run_full_test_suite():
    """Run the complete test suite for all templates."""
    from test_all_gee_templates import GEEAllTemplatesTester
    
    tester = GEEAllTemplatesTester()
    results = tester.run_all_tests()
    return results

def list_available_templates():
    """List all available templates for testing."""
    from test_all_gee_templates import GEEAllTemplatesTester
    
    tester = GEEAllTemplatesTester()
    
    print("📋 Available GEE Templates for Testing:")
    print("=" * 50)
    
    for template_name, config in tester.test_queries.items():
        print(f"\n🔧 {template_name.upper()}")
        print(f"   Description: {config['description']}")
        print(f"   Query: {config['query']}")
        print(f"   Location: {config['locations'][0]['matched_name']}")

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Test GEE Templates with various options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_gee_tests.py --list                    # List all available templates
  python run_gee_tests.py --template climate_analysis  # Test single template
  python run_gee_tests.py --all                     # Run full test suite
  python run_gee_tests.py                          # Run full test suite (default)
        """
    )
    
    parser.add_argument(
        '--template', '-t',
        type=str,
        help='Test a specific template by name'
    )
    
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Run full test suite (default)'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available templates'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    try:
        if args.list:
            list_available_templates()
            return
        
        elif args.template:
            result = run_single_template_test(args.template)
            if result:
                print(f"\n✅ Single template test completed for: {args.template}")
            return
        
        else:
            # Default: run full test suite
            print("🚀 Running full GEE templates test suite...")
            results = run_full_test_suite()
            if results:
                print(f"\n✅ Full test suite completed! Tested {len(results)} templates.")
            return
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user")
        return
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return

if __name__ == "__main__":
    main()
