#!/usr/bin/env python3
"""
Excel Template Migration CLI
Command-line interface for migrating Excel templates to the dynamic template system
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from excel_template_migrator import ExcelTemplateMigrator

def setup_parser():
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Migrate Excel templates to dynamic template system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate all Excel templates in default directory
  python migrate_excel_templates.py
  
  # Migrate specific Excel file
  python migrate_excel_templates.py --file my_template.xlsx
  
  # Migrate all files in custom directory
  python migrate_excel_templates.py --input-dir ./my_templates --output-dir ./migrated
  
  # Generate preview without actual migration
  python migrate_excel_templates.py --preview-only
  
  # Validate migrated templates
  python migrate_excel_templates.py --validate
        """
    )
    
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Specific Excel file to migrate"
    )
    
    parser.add_argument(
        "--input-dir", "-i",
        type=str,
        default="excel_templates",
        help="Directory containing Excel templates (default: excel_templates)"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="migrated_templates",
        help="Output directory for migrated templates (default: migrated_templates)"
    )
    
    parser.add_argument(
        "--preview-only", "-p",
        action="store_true",
        help="Preview migration without creating files"
    )
    
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="Validate migrated templates after migration"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing migrated templates"
    )
    
    parser.add_argument(
        "--verbose", "-V",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--report-format",
        choices=["text", "json", "markdown"],
        default="markdown",
        help="Report format (default: markdown)"
    )
    
    return parser

def preview_migration(migrator: ExcelTemplateMigrator, verbose: bool = False):
    """Preview what will be migrated"""
    print("🔍 Preview Mode - No files will be created")
    print("=" * 50)
    
    excel_files = migrator.scan_excel_templates()
    
    if not excel_files:
        print("❌ No Excel template files found")
        return
    
    print(f"📁 Found {len(excel_files)} Excel template files:")
    
    for file_path in excel_files:
        print(f"\n📄 {file_path.name}")
        
        if verbose:
            try:
                structure = migrator.analyze_excel_structure(file_path)
                if structure:
                    print(f"   Sheets: {len(structure.get('sheets', []))}")
                    print(f"   Max rows: {structure.get('total_rows', 0)}")
                    print(f"   Max cols: {structure.get('total_cols', 0)}")
                    
                    # Preview configuration
                    config = migrator.extract_template_config(file_path, structure)
                    print(f"   Name: {config.name}")
                    print(f"   Category: {config.category}")
                    print(f"   Days/week: {config.days_per_week}")
                    
                    # Preview exercises
                    exercises = migrator.extract_exercises(file_path, config)
                    print(f"   Exercises: {len(exercises)}")
                    
                    if exercises and len(exercises) <= 3:
                        for i, ex in enumerate(exercises[:3], 1):
                            print(f"     {i}. {ex.name} - {ex.sets}x{ex.reps}")
                        if len(exercises) > 3:
                            print(f"     ... and {len(exercises) - 3} more")
            except Exception as e:
                print(f"   ❌ Error analyzing: {e}")
    
    print(f"\n✅ Preview complete. {len(excel_files)} files ready for migration.")

def validate_templates(migrator: ExcelTemplateMigrator, verbose: bool = False):
    """Validate migrated templates"""
    print("🔍 Validating migrated templates...")
    print("=" * 50)
    
    if not migrator.output_dir.exists():
        print("❌ Output directory not found")
        return
    
    template_files = list(migrator.output_dir.glob("*_migrated.json"))
    
    if not template_files:
        print("❌ No migrated templates found")
        return
    
    print(f"📁 Found {len(template_files)} migrated templates")
    
    valid_count = 0
    invalid_count = 0
    validation_results = []
    
    for template_file in template_files:
        print(f"\n📄 Validating {template_file.name}...")
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_config = json.load(f)
            
            # Basic validation
            errors = []
            warnings = []
            
            # Check required fields
            required_fields = ["version", "metadata", "layout", "sections", "variables", "styling"]
            for field in required_fields:
                if field not in template_config:
                    errors.append(f"Missing required field: {field}")
            
            # Check metadata
            if "metadata" in template_config:
                metadata = template_config["metadata"]
                if not metadata.get("name"):
                    errors.append("Missing template name in metadata")
                if not metadata.get("description"):
                    warnings.append("Missing template description in metadata")
            
            # Check sections
            if "sections" in template_config:
                sections = template_config["sections"]
                if not sections:
                    errors.append("No sections defined")
                else:
                    for i, section in enumerate(sections):
                        if not section.get("id"):
                            errors.append(f"Section {i+1} missing id")
                        if not section.get("type"):
                            errors.append(f"Section {i+1} missing type")
            
            # Check variables
            if "variables" in template_config:
                variables = template_config["variables"]
                if not variables:
                    warnings.append("No variables defined")
            
            # Record results
            result = {
                "file": template_file.name,
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            validation_results.append(result)
            
            if len(errors) == 0:
                print(f"   ✅ Valid ({len(warnings)} warnings)")
                valid_count += 1
            else:
                print(f"   ❌ Invalid ({len(errors)} errors, {len(warnings)} warnings)")
                invalid_count += 1
                
                if verbose:
                    for error in errors:
                        print(f"      Error: {error}")
                    for warning in warnings:
                        print(f"      Warning: {warning}")
        
        except Exception as e:
            print(f"   ❌ Validation error: {e}")
            invalid_count += 1
            validation_results.append({
                "file": template_file.name,
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            })
    
    # Save validation results
    validation_file = migrator.output_dir / "validation_results.json"
    with open(validation_file, 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Validation Summary:")
    print(f"   Total: {len(template_files)}")
    print(f"   Valid: {valid_count}")
    print(f"   Invalid: {invalid_count}")
    print(f"   Success rate: {(valid_count/len(template_files)*100):.1f}%")
    print(f"   Results saved: {validation_file}")

def generate_report(results: dict, format_type: str = "markdown") -> str:
    """Generate migration report in specified format"""
    if format_type == "json":
        return json.dumps(results, indent=2, ensure_ascii=False)
    
    elif format_type == "text":
        report = []
        report.append("Excel Template Migration Report")
        report.append("=" * 40)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append(f"Total templates: {results['total']}")
        report.append(f"Successful: {results['successful']}")
        report.append(f"Failed: {results['failed']}")
        report.append(f"Success rate: {(results['successful']/results['total']*100):.1f}%")
        report.append("")
        
        if results['migrated_templates']:
            report.append("Successful migrations:")
            for template in results['migrated_templates']:
                report.append(f"  - {Path(template).name}")
        
        if results['errors']:
            report.append("Failed migrations:")
            for error in results['errors']:
                report.append(f"  - {Path(error['file']).name}: {error['error']}")
        
        return "\n".join(report)
    
    else:  # markdown
        report = []
        report.append("# Excel Template Migration Report")
        report.append("")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## Summary")
        report.append("")
        report.append(f"- **Total templates:** {results['total']}")
        report.append(f"- **Successful:** {results['successful']}")
        report.append(f"- **Failed:** {results['failed']}")
        report.append(f"- **Success rate:** {(results['successful']/results['total']*100):.1f}%")
        report.append("")
        
        if results['migrated_templates']:
            report.append("## ✅ Successful Migrations")
            report.append("")
            for template in results['migrated_templates']:
                report.append(f"- {Path(template).name}")
            report.append("")
        
        if results['errors']:
            report.append("## ❌ Failed Migrations")
            report.append("")
            for error in results['errors']:
                report.append(f"- **{Path(error['file']).name}**")
                report.append(f"  - Error: {error['error']}")
            report.append("")
        
        return "\n".join(report)

def main():
    """Main CLI function"""
    parser = setup_parser()
    args = parser.parse_args()
    
    print("🚀 Excel Template Migration CLI")
    print("=" * 40)
    
    # Initialize migrator
    migrator = ExcelTemplateMigrator()
    migrator.excel_templates_dir = Path(args.input_dir)
    migrator.output_dir = Path(args.output_dir)
    
    # Create output directory
    migrator.output_dir.mkdir(exist_ok=True)
    
    try:
        # Preview mode
        if args.preview_only:
            preview_migration(migrator, args.verbose)
            return
        
        # Validate mode
        if args.validate:
            validate_templates(migrator, args.verbose)
            return
        
        # Migration mode
        if args.file:
            # Migrate specific file
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                sys.exit(1)
            
            print(f"📄 Migrating single file: {file_path.name}")
            success, result = migrator.migrate_template(file_path)
            
            if success:
                print(f"✅ Migration successful: {result}")
            else:
                print(f"❌ Migration failed: {result}")
                sys.exit(1)
        
        else:
            # Migrate all files
            print(f"📁 Migrating templates from: {migrator.excel_templates_dir}")
            print(f"📁 Output directory: {migrator.output_dir}")
            print("")
            
            results = migrator.migrate_all_templates()
            
            # Print results
            print("📊 Migration Results:")
            print(f"   Total templates: {results['total']}")
            print(f"   Successful: {results['successful']}")
            print(f"   Failed: {results['failed']}")
            
            if results['total'] > 0:
                print(f"   Success rate: {(results['successful']/results['total']*100):.1f}%")
            
            print("")
            
            # Generate and save report
            report = generate_report(results, args.report_format)
            
            report_extension = {
                "text": ".txt",
                "json": ".json",
                "markdown": ".md"
            }[args.report_format]
            
            report_file = migrator.output_dir / f"migration_report{report_extension}"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"📄 Migration report saved: {report_file}")
            
            # Show errors if any
            if results['errors']:
                print("\n❌ Migration Errors:")
                for error in results['errors']:
                    print(f"   {Path(error['file']).name}: {error['error']}")
            
            # Validate if requested
            if args.validate:
                print("\n" + "=" * 50)
                validate_templates(migrator, args.verbose)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
