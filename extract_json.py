import json
import re
import sys

import pdfplumber


def clean_text(text):
    """Remove extra whitespace and clean up text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_door_type(door_type_text):
    """
    Parse door type text to extract code and dimensions.
    Examples:
    - "MD\n1250(W)x2240(H)\n1" -> code="MD/1", dimensions="1250(W)x2240(H)"
    - "FDM\n1" -> code="FDM/1", dimensions=""
    - "DM\n1000(W)x2170(H)\n10" -> code="DM/10", dimensions="1000(W)x2170(H)"
    - "FD1 1-HR FIRE RATED\n10S 1000(W)x2190(H)" -> code="FD1/10S", dimensions="1000(W)x2190(H)"
    """
    if not door_type_text:
        return None, None

    lines = [l.strip() for l in door_type_text.strip().split("\n") if l.strip()]

    if len(lines) == 0:
        return None, None

    code = lines[0]

    # Filter out invalid door codes (metadata, incomplete entries, etc.)
    if not re.search(r"[A-Z]", code):
        return None, None
    if code.startswith("000(W)"):
        return None, None
    if "PRECINCT" in code or "DRAWING" in code or "PROJECT" in code:
        return None, None

    # Clean up door code - remove fire rating info embedded in the code
    # e.g., "FD1 1-HR FIRE RATED" -> "FD1", "FMD1 1-HR FIRE RATED" -> "FMD1"
    # Also handle dimensions embedded in code like "GD 2100(W)x2190(H)" or "FMD2 1100(W)x2190(H)"
    code_parts = code.split()
    clean_code = code_parts[0]  # First part is the actual door code

    # Check if there's a dimension in the code line itself
    embedded_dimension = ""
    for part in code_parts:
        if re.search(r"\d+\(W\)x\d+\(H\)", part):
            embedded_dimension = part
            break

    dimensions = embedded_dimension
    variant = ""

    # Check for dimensions in format XXX(W)xXXX(H) and variants
    for line in lines[1:]:
        # Check if line has dimensions pattern
        if re.search(r"\d+\(W\)x\d+\(H\)", line):
            # Check if variant is embedded in same line (e.g., "10S 1000(W)x2190(H)")
            parts = line.split()
            if len(parts) >= 2:
                # Check if first part is variant (digit or digit+letter combo)
                first_part = parts[0]
                if first_part.isdigit() or re.match(r"^\d+[A-Z]+$", first_part):
                    variant = first_part
                    # Reconstruct dimensions from remaining parts
                    dimensions = " ".join(parts[1:])
                    # Clean up dimensions to just the XXX(W)xXXX(H) part
                    dim_match = re.search(r"\d+\(W\)x\d+\(H\)", dimensions)
                    if dim_match:
                        dimensions = dim_match.group(0)
                else:
                    # No variant in this line, just dimensions
                    if not dimensions:  # Only set if not already set from code line
                        dimensions = line
            else:
                # Single part with dimensions
                if not dimensions:  # Only set if not already set from code line
                    dimensions = line
        else:
            # Check if line starts with a variant (even if followed by extra text)
            # e.g., "21 (MIN 850mm CLEAR WHEN ONE-DOOR LEAF IS OPEN)"
            parts = line.split()
            if parts and (parts[0].isdigit() or re.match(r"^\d+[A-Z]+$", parts[0])):
                if not variant:  # Only set variant if not already set
                    variant = parts[0]

    # Build final code
    if variant:
        final_code = f"{clean_code}/{variant}"
    else:
        final_code = clean_code

    return final_code, dimensions


def extract_doors_from_table(table):
    """
    Extract door schedule entries from a table.
    The table has rows with labels in column 0: DOOR TYPE, FIRE-RATING, DESCRIPTION, LOCATION, REMARKS
    Each subsequent column represents a different door.
    There can be multiple DOOR TYPE sections within the same table.
    """
    if not table or len(table) < 2:
        return []

    doors = []

    # Find all DOOR TYPE row indices (there can be multiple sections)
    door_type_row_indices = []
    for i, row in enumerate(table):
        if row and row[0] and row[0].strip() == "DOOR TYPE":
            door_type_row_indices.append(i)

    if not door_type_row_indices:
        return []

    # Process each DOOR TYPE section
    for section_idx, door_type_row_idx in enumerate(door_type_row_indices):
        # Find the end of this section (next DOOR TYPE or end of table)
        section_end = (
            door_type_row_indices[section_idx + 1]
            if section_idx + 1 < len(door_type_row_indices)
            else len(table)
        )

        # Find row indices for fields within this section
        fire_rating_row_idx = None
        description_row_idx = None
        location_row_idx = None
        remarks_row_idx = None

        for i in range(door_type_row_idx, section_end):
            row = table[i]
            if row and row[0]:
                label = row[0].strip()
                if label == "FIRE-RATING" or label == "FIRE RATING":
                    fire_rating_row_idx = i
                elif label == "DESCRIPTION":
                    description_row_idx = i
                elif label == "LOCATION":
                    location_row_idx = i
                elif label == "REMARKS":
                    remarks_row_idx = i
                elif label == "ELEVATION":
                    # Stop processing at ELEVATION row - ignore drawing data
                    section_end = i
                    break

        # Extract data from each column (skip column 0 which has labels)
        door_type_row = table[door_type_row_idx]
        fire_rating_row = (
            table[fire_rating_row_idx] if fire_rating_row_idx is not None else []
        )
        description_row = (
            table[description_row_idx] if description_row_idx is not None else []
        )
        location_row = table[location_row_idx] if location_row_idx is not None else []
        remarks_row = table[remarks_row_idx] if remarks_row_idx is not None else []

        # Process each column
        for col_idx in range(1, len(door_type_row)):
            door_type_text = (
                door_type_row[col_idx] if col_idx < len(door_type_row) else None
            )

            # Skip empty columns or columns with non-door data
            if not door_type_text or not door_type_text.strip():
                continue

            # Skip columns with drawing metadata
            if "TENDER DRAWING" in door_type_text or "DRAWING TITLE" in door_type_text:
                continue

            # Check if next column(s) have continuation data (e.g., "000(W)x2190(H)" to complete "1000(W)x2190(H)")
            next_col_idx = col_idx + 1
            while next_col_idx < len(door_type_row) and next_col_idx < col_idx + 3:
                next_text = (
                    door_type_row[next_col_idx]
                    if next_col_idx < len(door_type_row)
                    else None
                )
                if (
                    next_text
                    and next_text.strip()
                    and re.match(r"^\d+\(W\)x\d+\(H\)$", next_text.strip())
                ):
                    # This looks like a continuation, merge it
                    door_type_text = door_type_text + " " + next_text
                    break
                next_col_idx += 1

            # Parse door type and dimensions
            door_code, dimensions = parse_door_type(door_type_text)

            if not door_code:
                continue

            # Extract other fields
            fire_rating = (
                clean_text(fire_rating_row[col_idx])
                if col_idx < len(fire_rating_row) and fire_rating_row[col_idx]
                else ""
            )
            description = (
                clean_text(description_row[col_idx])
                if col_idx < len(description_row) and description_row[col_idx]
                else ""
            )
            location = (
                clean_text(location_row[col_idx])
                if col_idx < len(location_row) and location_row[col_idx]
                else ""
            )
            remarks = (
                clean_text(remarks_row[col_idx])
                if col_idx < len(remarks_row) and remarks_row[col_idx]
                else ""
            )

            # Check if this column contains multiple doors
            # Detect patterns like "DB DB", "FMD2 FMD2 FMD2", "FRS2 FRS2 FRS2 FRS2 FRS2 FRS2", etc.
            has_multiple_doors = False

            # Check for repeating door codes
            first_word = door_type_text.split()[0] if door_type_text.split() else ""
            if first_word and first_word in door_type_text[len(first_word) :]:
                has_multiple_doors = True

            # Also check for multiple dimensions
            if door_type_text.count("(W)x") > 1:
                has_multiple_doors = True

            if has_multiple_doors:
                # This column has multiple doors - try to split them
                split_doors = split_multi_door_column(
                    door_type_text, fire_rating, description, location, remarks
                )
                doors.extend(split_doors)
            else:
                door_entry = {
                    "door_type": door_code,
                    "dimensions": dimensions,
                    "fire_rating": fire_rating,
                    "description": description,
                    "location": location,
                    "remarks": remarks,
                }
                doors.append(door_entry)

    return doors


def split_multi_door_column(
    door_type_text, fire_rating, description, location, remarks
):
    """
    Handle columns that contain multiple doors.
    Generic handler for patterns like:
    - "DB DB\n9 900(W)x2190(H) 10 1 000(W)x2190(H)"
    - "FMD2 FMD2 FMD2\n475(W)x2190(H) 600(W)x2190(H) 800(W)x2190(H)\n4A 6 8"
    - "FRS2 FRS2 FRS2 FRS2 FRS2 FRS2\n1600(W)x2700(H) 2200(W)x2400(H)...\n16 22 61 32 35 40"
    """
    doors = []

    lines = [l.strip() for l in door_type_text.strip().split("\n") if l.strip()]

    if len(lines) < 2:
        return doors

    # Extract the base door code (first word of first line)
    first_line_parts = lines[0].split()
    if not first_line_parts:
        return doors

    base_code = first_line_parts[0]

    # Count how many times the base code appears
    num_doors = first_line_parts.count(base_code)

    if num_doors < 2:
        return doors

    # Strategy: Extract dimensions and variants separately, then match them up
    # 1. Extract all dimensions from all lines
    all_dimensions = re.findall(r"\d+\(W\)x\d+\(H\)", door_type_text)

    # Fix split dimensions (like "1" + "000(W)x2190(H)" = "1000(W)x2190(H)")
    all_tokens = []
    for line in lines[1:]:
        all_tokens.extend(line.split())

    for i, dim in enumerate(all_dimensions):
        if dim.startswith("000(W)x"):
            # Look for a preceding "1" to reconstruct "1000"
            for j, tok in enumerate(all_tokens):
                if (
                    tok == dim
                    and j > 0
                    and all_tokens[j - 1].isdigit()
                    and len(all_tokens[j - 1]) == 1
                ):
                    all_dimensions[i] = all_tokens[j - 1] + dim
                    break

    # 2. Extract variants - prioritize finding a dedicated variant line
    # Look for a line that has num_doors space-separated tokens that are NOT dimensions
    all_variants = []

    for line in lines[1:]:
        parts = line.split()
        # Check if this line could be a variant line (no dimensions, multiple tokens)
        has_dimension = any(re.search(r"\d+\(W\)x\d+\(H\)", part) for part in parts)

        if not has_dimension and len(parts) >= num_doors:
            # This might be the variant line - extract variants
            for part in parts:
                # Match patterns like "16", "22", "4A", "18G", "15LPG", "27"
                # But NOT dimension widths like "1600", "2800", "4000"
                if part[0].isdigit():
                    # Extract variant (digits optionally followed by letters)
                    variant_match = re.match(r"^(\d+[A-Z]*)(?:\s|\(|$)", part + " ")
                    if variant_match:
                        variant = variant_match.group(1)
                        # Reject if it looks like a dimension width (3+ digits without letters)
                        if len(variant) <= 2 or not variant.isdigit():
                            all_variants.append(variant)
                            if len(all_variants) >= num_doors:
                                break

            if len(all_variants) >= num_doors:
                break

    # 3. If we didn't find a dedicated variant line, try extracting from mixed lines
    if len(all_variants) < num_doors:
        for line in lines[1:]:
            parts = line.split()
            for part in parts:
                if not re.search(r"\(W\)x\(H\)", part) and part[0].isdigit():
                    variant_match = re.match(r"^(\d+[A-Z]*)(?:\s|\(|$)", part + " ")
                    if variant_match:
                        variant = variant_match.group(1)
                        # Avoid dimension widths: reject 3+ digit numbers without letters
                        if (
                            len(variant) <= 2 or not variant.isdigit()
                        ) and variant not in all_variants:
                            all_variants.append(variant)
                            if len(all_variants) >= num_doors:
                                break

    # Create door entries
    for i in range(num_doors):
        variant = all_variants[i] if i < len(all_variants) else ""
        dims = all_dimensions[i] if i < len(all_dimensions) else ""

        door_type = f"{base_code}/{variant}" if variant else base_code

        doors.append(
            {
                "door_type": door_type,
                "dimensions": dims,
                "fire_rating": fire_rating,
                "description": description,
                "location": location,
                "remarks": remarks,
            }
        )

    # If we successfully created doors, return them
    if doors:
        return doors

    # Fallback: old FD1 FD1 handling (kept for compatibility)
    if "FD1 FD1" in door_type_text:
        # Pattern: FD1 FD1\n650(W)x2190(H) 800(W)x2190(H)\n6A 8A
        lines = [l.strip() for l in door_type_text.split("\n") if l.strip()]

        # Find dimensions and variants
        dimensions_list = []
        variants_list = []

        for line in lines:
            if "(W)x" in line:
                # Extract all dimensions from this line
                dims = re.findall(r"\d+\(W\)x\d+\(H\)", line)
                dimensions_list.extend(dims)
            elif re.match(r"^\d+[A-Z]\s+\d+[A-Z]$", line):
                # Line with variants like "6A 8A"
                variants_list = line.split()

        # Create door entries
        num_doors = max(len(dimensions_list), len(variants_list), 2)
        for i in range(num_doors):
            variant = variants_list[i] if i < len(variants_list) else ""
            dims = dimensions_list[i] if i < len(dimensions_list) else ""

            doors.append(
                {
                    "door_type": f"FD1/{variant}" if variant else "FD1",
                    "dimensions": dims,
                    "fire_rating": fire_rating,
                    "description": description,
                    "location": location,
                    "remarks": remarks,
                }
            )

    return doors


def is_valid_door_entry(door):
    """Check if a door entry is valid and not metadata."""
    door_type = door.get("door_type", "").strip()

    # Filter out invalid entries
    invalid_patterns = [
        "TENDER DRAWING",
        "DRAWING TITLE",
        "PRECINCT NAME",
        "PROJECT TITLE",
        "LOT NO",
        "MUKIM NO",
        "JOB TITLE",
        "DRAWN BY",
        "CHECKED BY",
        "SCALE",
        "DATE",
        "REV",
        "DESCRIPTION",
    ]

    for pattern in invalid_patterns:
        if pattern in door_type.upper():
            return False

    # Filter out entries that are just dimensions without code
    if door_type.startswith("000(W)x") or re.match(r"^\d+\(W\)x\d+\(H\)$", door_type):
        return False

    # Must have at least letters in the door type
    if not re.search(r"[A-Z]", door_type):
        return False

    return True


def process_page(page, page_num):
    """Process a single page and extract door schedule data."""
    doors = []

    try:
        # Extract tables from the page
        tables = page.extract_tables()

        if not tables:
            print(f"  No tables found on page {page_num}")
            return doors

        print(f"  Found {len(tables)} table(s) on page {page_num}")

        # Process each table
        for table_idx, table in enumerate(tables):
            table_doors = extract_doors_from_table(table)
            # Filter out invalid entries
            valid_doors = [d for d in table_doors if is_valid_door_entry(d)]
            if valid_doors:
                print(
                    f"    Table {table_idx + 1}: Extracted {len(valid_doors)} door(s)"
                )
                doors.extend(valid_doors)

    except Exception as e:
        print(f"  Error processing page {page_num}: {e}")

    return doors


def main():
    import os

    # Check for help flag
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        print("=" * 80)
        print("Door Schedule Extractor - Command Line Tool")
        print("=" * 80)
        print("\nUsage:")
        print("  python extract_json.py <input_pdf> [output_json]")
        print("\nArguments:")
        print("  input_pdf    : Path to the PDF file to extract (required)")
        print("  output_json  : Path to output JSON file (optional)")
        print("                 Default: <input_filename>_door_schedule.json")
        print("\nExamples:")
        print("  python extract_json.py door_schedule.pdf")
        print("  python extract_json.py door_schedule.pdf output.json")
        print("  python extract_json.py path/to/file.pdf path/to/output.json")
        print("\n" + "=" * 80)
        sys.exit(0)

    # Get PDF path from command line argument
    if len(sys.argv) < 2:
        print("Error: PDF file path is required!")
        print("\nUsage: python extract_json.py <input_pdf> [output_json]")
        print("Use -h or --help for more information")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    # Determine output filename
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        # Extract base name from pdf_path and create output filename
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_file = f"{base_name}_door_schedule.json"

    all_doors = []

    print(f"Processing PDF: {pdf_path}")
    print("=" * 80)

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}\n")

        for page_num, page in enumerate(pdf.pages, start=1):
            print(f"Processing page {page_num}...")
            page_doors = process_page(page, page_num)
            all_doors.extend(page_doors)
            print()

    # Post-processing: clean up and handle special cases
    for door in all_doors:
        # Remove "FIRE-RATING", "DESCRIPTION", etc. if they leaked into the content
        door["fire_rating"] = door["fire_rating"].replace("FIRE-RATING", "").strip()
        door["description"] = door["description"].replace("DESCRIPTION", "").strip()
        door["location"] = door["location"].replace("LOCATION", "").strip()
        door["remarks"] = door["remarks"].replace("REMARKS", "").strip()

        # Handle missing dimensions for known door types
        if not door["dimensions"]:
            # Try to extract from door type if it contains dimensions
            match = re.search(r"(\d+\(W\)x\d+\(H\))", door["door_type"])
            if match:
                door["dimensions"] = match.group(1)

    # Save to JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_doors, f, indent=4, ensure_ascii=False)

    print("=" * 80)
    print(f"Extraction complete!")
    print(f"Total doors extracted: {len(all_doors)}")
    print(f"Data saved to: {output_file}")

    # Print summary
    print("\nDoor types summary:")
    door_type_counts = {}
    for door in all_doors:
        dt = door["door_type"]
        door_type_counts[dt] = door_type_counts.get(dt, 0) + 1

    for dt, count in sorted(door_type_counts.items()):
        print(f"  {dt}: {count}")

    # Print first 3 entries as examples
    print("\nFirst 3 door entries:")
    for i, door in enumerate(all_doors[:3], start=1):
        print(f"\n{i}. {door['door_type']}")
        print(f"   Dimensions: {door['dimensions']}")
        print(f"   Fire Rating: {door['fire_rating'][:80]}")
        print(f"   Description: {door['description'][:80]}")
        print(f"   Location: {door['location'][:80]}")
        print(f"   Remarks: {door['remarks'][:80]}")


if __name__ == "__main__":
    main()
