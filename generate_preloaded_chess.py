#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate preloaded chess reports JSON files.

This script scans ./preloaded_reports/ for .txt and .md files,
and generates JSON files that the chess analyzer app can fetch.

Usage:
    python generate_preloaded_chess.py

Output:
    ./preloaded/index.json - List of available report files
    ./preloaded/reports.json - Contents of all report files
"""

import os
import json
import argparse

def process_file(file_path):
    """Read a file and return its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"  Warning: Could not read {file_path}: {e}")
        return None

def generate_preloaded_reports(input_dir='./preloaded_reports', output_dir='./preloaded'):
    """Generate JSON files from preloaded report files."""

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Check input directory
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        return

    files_data = {}
    file_list = []

    # Get all files in the directory
    entries = os.listdir(input_dir)

    # Filter for .txt and .md files (not directories)
    text_files = [f for f in entries
                  if os.path.isfile(os.path.join(input_dir, f))
                  and (f.endswith('.txt') or f.endswith('.md'))
                  and not f.startswith('.')]

    # Sort files naturally (handles numbers correctly)
    text_files.sort(key=lambda x: x.lower())

    print(f"Found {len(text_files)} report files in {input_dir}")

    for filename in text_files:
        file_path = os.path.join(input_dir, filename)
        content = process_file(file_path)

        if content is not None:
            files_data[filename] = content
            file_list.append({
                'name': filename,
                'size': len(content)
            })
            print(f"  - {filename} ({len(content):,} chars)")

    if len(file_list) == 0:
        print("No .txt or .md files found.")
        return

    # Save all reports to a single JSON file
    reports_path = os.path.join(output_dir, 'reports.json')
    with open(reports_path, 'w', encoding='utf-8') as f:
        json.dump(files_data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved reports to {reports_path}")

    # Save index of all files
    index_path = os.path.join(output_dir, 'index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({'files': file_list, 'count': len(file_list)}, f, ensure_ascii=False, indent=2)
    print(f"Saved index to {index_path}")

    print(f"\n✅ Generated {len(file_list)} preloaded report(s)")
    print(f"📁 Output directory: {output_dir}")

    return file_list

def main():
    parser = argparse.ArgumentParser(description='Generate preloaded chess reports JSON files.')
    parser.add_argument('-i', '--input', default='./preloaded_reports',
                        help='Input directory containing report files (default: ./preloaded_reports)')
    parser.add_argument('-o', '--output', default='./preloaded',
                        help='Output directory for JSON files (default: ./preloaded)')

    args = parser.parse_args()

    generate_preloaded_reports(args.input, args.output)

if __name__ == "__main__":
    main()
