import sys
import math
import csv

def read_xfem_crack_tips(filepath):
    """
    Reads the crack tips estimated by XFEM from a text file.
    Assumes CSV format: Tip, X, Y, Z
    Returns a list of (X, Y) tuples.
    """
    xfem_tips = []
    try:
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            header = next(reader) # Skip header
            for row in reader:
                if len(row) >= 3:
                    # Parse X and Y
                    xfem_tips.append((float(row[1]), float(row[2])))
    except FileNotFoundError:
        print(f"Error: {filepath} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        sys.exit(1)
    return xfem_tips

def calculate_analytical_crack_tips(x0, y0, delta_a, angles_deg):
    """
    Calculates analytical crack tip positions based on the formula:
    x_i = x_{i-1} + delta_a * cos(theta)
    y_i = y_{i-1} + delta_a * sin(theta)

    Args:
        x0, y0: Initial crack tip position
        delta_a: Crack increment size
        angles_deg: List of angles in degrees for each step
    """
    analytical_tips = [(x0, y0)]

    current_x = x0
    current_y = y0

    for angle_deg in angles_deg:
        angle_rad = math.radians(angle_deg)
        current_x = current_x + delta_a * math.cos(angle_rad)
        current_y = current_y + delta_a * math.sin(angle_rad)
        analytical_tips.append((current_x, current_y))

    return analytical_tips

def calculate_error(xfem_tips, analytical_tips):
    """
    Calculates the Euclidean distance error between XFEM and analytical tips.
    """
    errors = []
    min_len = min(len(xfem_tips), len(analytical_tips))

    for i in range(min_len):
        x_xfem, y_xfem = xfem_tips[i]
        x_ana, y_ana = analytical_tips[i]

        error = math.sqrt((x_xfem - x_ana)**2 + (y_xfem - y_ana)**2)
        errors.append(error)

    return errors

def main():
    if len(sys.argv) < 5:
        print("Usage: python compare_crack_tips.py <xfem_tips_file> <x0> <y0> <delta_a> <angle1> [angle2 ...]")
        print("Example: python compare_crack_tips.py crack_tips.txt 0.0 0.0 0.5 30 45 60")
        sys.exit(1)

    xfem_file = sys.argv[1]
    try:
        x0 = float(sys.argv[2])
        y0 = float(sys.argv[3])
        delta_a = float(sys.argv[4])
        angles = [float(a) for a in sys.argv[5:]]
    except ValueError:
        print("Error: Initial coordinates, delta_a, and angles must be numbers.")
        sys.exit(1)

    print(f"Loading XFEM crack tips from {xfem_file}...")
    xfem_tips = read_xfem_crack_tips(xfem_file)

    print(f"Calculating analytical crack tips (x0={x0}, y0={y0}, delta_a={delta_a})...")
    analytical_tips = calculate_analytical_crack_tips(x0, y0, delta_a, angles)

    print("\nComparison Results:")
    print("-" * 65)
    print(f"{'Step':<5} | {'XFEM (X, Y)':<20} | {'Analytical (X, Y)':<20} | {'Error':<10}")
    print("-" * 65)

    errors = calculate_error(xfem_tips, analytical_tips)

    for i in range(len(errors)):
        xfem_str = f"({xfem_tips[i][0]:.4f}, {xfem_tips[i][1]:.4f})"
        ana_str = f"({analytical_tips[i][0]:.4f}, {analytical_tips[i][1]:.4f})"
        print(f"{i:<5} | {xfem_str:<20} | {ana_str:<20} | {errors[i]:.4f}")

    if len(xfem_tips) != len(analytical_tips):
        print(f"\nWarning: Number of XFEM tips ({len(xfem_tips)}) does not match number of analytical tips ({len(analytical_tips)}).")
        print("Comparison was only performed for the overlapping steps.")

if __name__ == "__main__":
    main()
