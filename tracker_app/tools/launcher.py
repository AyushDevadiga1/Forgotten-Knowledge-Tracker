"""
Learning Tracker Launcher
Main entry point for starting the application in different modes
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path


class Launcher:
    """Application launcher with multiple modes"""

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def launch_cli(self, args):
        """Launch CLI interface"""
        print("\n  🖥️  Starting CLI Interface...")
        try:
            from enhanced_review_interface import EnhancedReviewInterface
            app = EnhancedReviewInterface()
            app.run()
        except ImportError as e:
            print(f"  ❌ Error: {e}")
            sys.exit(1)

    def launch_web(self, args):
        """Launch web dashboard"""
        port = args.port or 5000
        print(f"\n  🌐 Starting Web Dashboard on http://localhost:{port}")
        print(f"     Press Ctrl+C to stop\n")
        
        try:
            from api_server import run_api_server
            run_api_server(debug=args.debug, port=port)
        except ImportError as e:
            print(f"  ❌ Error: {e}")
            print(f"     Please install Flask: pip install flask")
            sys.exit(1)

    def launch_config(self, args):
        """Launch configuration wizard"""
        print("\n  ⚙️  Starting Configuration Wizard...\n")
        try:
            from config_manager import ConfigurationWizard
            wizard = ConfigurationWizard()
            wizard.run()
        except ImportError as e:
            print(f"  ❌ Error: {e}")
            sys.exit(1)

    def launch_test(self, args):
        """Launch test suite"""
        print("\n  🧪 Running Test Suite...\n")
        try:
            from test_new_system import run_tests
            run_tests(verbosity=args.verbose)
        except ImportError as e:
            print(f"  ❌ Error: {e}")
            sys.exit(1)

    def launch_backup(self, args):
        """Backup database"""
        print("\n  💾 Creating Backup...")
        try:
            from core.batch_operations import BackupManager
            backup = BackupManager()
            desc = args.description or ''
            backup_file = backup.create_backup(desc)
            print(f"  ✓ Backup created: {backup_file}\n")
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            sys.exit(1)

    def launch_restore(self, args):
        """Restore from backup"""
        if not args.backup_file:
            print("\n  ❌ Error: --backup-file required\n")
            sys.exit(1)
        
        print(f"\n  💾 Restoring from backup...")
        try:
            from core.batch_operations import BackupManager
            backup = BackupManager()
            if backup.restore_from_backup(args.backup_file):
                print(f"  ✓ Restored successfully!\n")
            else:
                print(f"  ❌ Restore failed\n")
                sys.exit(1)
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            sys.exit(1)

    def launch_import(self, args):
        """Import data"""
        if not args.file:
            print("\n  ❌ Error: --file required\n")
            sys.exit(1)
        
        file_path = args.file
        if not os.path.exists(file_path):
            print(f"\n  ❌ Error: File not found: {file_path}\n")
            sys.exit(1)
        
        print(f"\n  📥 Importing from {file_path}...")
        
        try:
            from core.batch_operations import DataImporter
            importer = DataImporter()
            
            if file_path.endswith('.json'):
                result = importer.import_from_json(file_path)
            elif file_path.endswith('.csv'):
                result = importer.import_from_csv(file_path)
            elif file_path.endswith('.txt'):  # Anki
                result = importer.import_from_anki(file_path)
            else:
                print(f"  ❌ Error: Unsupported file format\n")
                sys.exit(1)
            
            print(f"  ✓ Imported {result['successful']} items")
            if result['failed'] > 0:
                print(f"  ⚠️  {result['failed']} items failed")
            print()
            
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            sys.exit(1)

    def launch_export(self, args):
        """Export data"""
        format_type = args.format or 'json'
        output = args.output or f'export.{format_type}'
        
        print(f"\n  📤 Exporting to {format_type}...")
        
        try:
            from core.batch_operations import DataExporter
            exporter = DataExporter()
            
            if format_type == 'json':
                exporter.export_to_json(output, include_history=True)
            elif format_type == 'csv':
                exporter.export_to_csv(output)
            elif format_type == 'anki':
                exporter.export_to_anki(output)
            else:
                print(f"  ❌ Error: Unsupported format: {format_type}\n")
                sys.exit(1)
            
            print(f"  ✓ Exported to {output}\n")
            
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            sys.exit(1)

    def show_info(self):
        """Show system information"""
        print("\n" + "="*60)
        print("  LEARNING TRACKER - SYSTEM INFORMATION")
        print("="*60)
        
        try:
            from config_manager import Config
            config = Config()
            app_config = config.get_app_config()
            
            print(f"\n  App: {app_config.get('name')} v{app_config.get('version')}")
            print(f"  Environment: {app_config.get('environment')}")
            
            # Database info
            db_path = config.get('database.path')
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path) / 1024
                print(f"  Database: {db_path} ({db_size:.1f} KB)")
            
            # Feature status
            print(f"\n  Features Enabled:")
            features = config.get('features', {})
            for feature, enabled in features.items():
                status = "✓" if enabled else "✗"
                print(f"     {status} {feature}")
            
            # Validation
            validation = config.validate()
            print(f"\n  Configuration: {'Valid ✓' if validation['valid'] else 'Invalid ✗'}")
            if not validation['valid']:
                for issue in validation['issues']:
                    print(f"     • {issue}")
            
        except Exception as e:
            print(f"\n  ❌ Error: {e}")
        
        print()

    def main(self):
        """Parse arguments and launch"""
        parser = argparse.ArgumentParser(
            description='Learning Tracker - Master your knowledge with spaced repetition',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
Examples:
  python launcher.py cli              # Start CLI interface
  python launcher.py web --port 8000  # Start web on port 8000
  python launcher.py config           # Configure application
  python launcher.py test             # Run tests
  python launcher.py info             # Show system info
            '''
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        
        # CLI command
        subparsers.add_parser('cli', help='Start CLI interface')
        
        # Web command
        web_parser = subparsers.add_parser('web', help='Start web dashboard')
        web_parser.add_argument('--port', type=int, help='API port (default: 5000)')
        web_parser.add_argument('--debug', action='store_true', help='Debug mode')
        
        # Config command
        subparsers.add_parser('config', help='Configure application')
        
        # Test command
        test_parser = subparsers.add_parser('test', help='Run test suite')
        test_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
        
        # Backup command
        backup_parser = subparsers.add_parser('backup', help='Create backup')
        backup_parser.add_argument('--description', help='Backup description')
        
        # Restore command
        restore_parser = subparsers.add_parser('restore', help='Restore from backup')
        restore_parser.add_argument('--backup-file', required=True, help='Backup file path')
        
        # Import command
        import_parser = subparsers.add_parser('import', help='Import data')
        import_parser.add_argument('--file', required=True, help='Import file (json/csv/txt)')
        
        # Export command
        export_parser = subparsers.add_parser('export', help='Export data')
        export_parser.add_argument('--format', choices=['json', 'csv', 'anki'], help='Export format')
        export_parser.add_argument('--output', help='Output file path')
        
        # Info command
        subparsers.add_parser('info', help='Show system information')
        
        args = parser.parse_args()
        
        if not args.command:
            self.show_info()
            return
        
        # Route to appropriate launcher
        if args.command == 'cli':
            self.launch_cli(args)
        elif args.command == 'web':
            self.launch_web(args)
        elif args.command == 'config':
            self.launch_config(args)
        elif args.command == 'test':
            self.launch_test(args)
        elif args.command == 'backup':
            self.launch_backup(args)
        elif args.command == 'restore':
            self.launch_restore(args)
        elif args.command == 'import':
            self.launch_import(args)
        elif args.command == 'export':
            self.launch_export(args)
        elif args.command == 'info':
            self.show_info()


if __name__ == '__main__':
    launcher = Launcher()
    launcher.main()
