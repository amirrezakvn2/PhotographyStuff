import sys
import math
try:
    from odbAccess import openOdb
except ImportError:
    print("Warning: odbAccess module not found. This script must be run within the Abaqus Python environment.")

def extract_data_and_calculate_tip(odb_path, step_name=None, frame_idx=-1, instance_name=None):
    try:
        odb = openOdb(path=odb_path)
    except Exception as e:
        print("Failed to open ODB:", e)
        return

    if step_name is None:
        step = odb.steps.values()[-1]
    else:
        if step_name in odb.steps:
            step = odb.steps[step_name]
        else:
            print("Step %s not found" % step_name)
            odb.close()
            return

    try:
        frame = step.frames[frame_idx]
    except IndexError:
        print("Frame index %d out of bounds" % frame_idx)
        odb.close()
        return

    try:
        philsm_field = frame.fieldOutputs['PHILSM']
        psilsm_field = frame.fieldOutputs['PSILSM']
        statusxfem_field = frame.fieldOutputs['STATUSXFEM']
    except KeyError as e:
        print("Required field output not found: %s" % e)
        odb.close()
        return

    # Extract node coordinates
    if instance_name is None:
        # Just use the first instance
        instance = odb.rootAssembly.instances.values()[0]
    else:
        if instance_name in odb.rootAssembly.instances:
            instance = odb.rootAssembly.instances[instance_name]
        else:
            print("Instance %s not found" % instance_name)
            odb.close()
            return

    nodes = instance.nodes
    elements = instance.elements

    node_coords = {}
    for node in nodes:
        node_coords[node.label] = node.coordinates

    # Get values at nodes (assuming PHILSM and PSILSM are nodal fields)
    philsm_values = {}
    for value in philsm_field.values:
        if value.nodeLabel is not None:
            philsm_values[value.nodeLabel] = value.data

    psilsm_values = {}
    for value in psilsm_field.values:
        if value.nodeLabel is not None:
            psilsm_values[value.nodeLabel] = value.data

    # Save extracted data to a file
    with open("xfem_extracted_data.txt", "w") as f:
        f.write("NodeLabel, X, Y, Z, PHILSM, PSILSM\n")
        for node_label in node_coords:
            coords = node_coords[node_label]
            phi = philsm_values.get(node_label, 0.0)
            psi = psilsm_values.get(node_label, 0.0)
            if node_label in philsm_values or node_label in psilsm_values:
                f.write("%d, %f, %f, %f, %f, %f\n" % (node_label, coords[0], coords[1], coords[2], phi, psi))

    print("Data extracted and saved to xfem_extracted_data.txt")

    # To calculate crack tip coordinates, we search for elements where both PHILSM and PSILSM cross zero
    # STATUSXFEM is element-based or integration point-based. We can use it to filter cracked elements.
    crack_tips = []

    # Get element STATUSXFEM values
    element_status = {}
    for value in statusxfem_field.values:
        if value.elementLabel is not None:
            # If multiple integration points, we can just average or take max
            if value.elementLabel not in element_status:
                element_status[value.elementLabel] = value.data
            else:
                element_status[value.elementLabel] = max(element_status[value.elementLabel], value.data)

    for element in elements:
        # Check if element has STATUSXFEM
        status = element_status.get(element.label, 0.0)
        # Element with crack tip typically has STATUSXFEM > 0.0 and < 1.0, or we can just check all enriched elements
        if status <= 0.0:
            continue

        el_nodes = element.connectivity
        el_phi = [philsm_values.get(nl, None) for nl in el_nodes]
        el_psi = [psilsm_values.get(nl, None) for nl in el_nodes]

        if None in el_phi or None in el_psi:
            continue

        # Check if PHILSM and PSILSM cross zero in this element
        min_phi, max_phi = min(el_phi), max(el_phi)
        min_psi, max_psi = min(el_psi), max(el_psi)

        if min_phi <= 0.0 and max_phi >= 0.0 and min_psi <= 0.0 and max_psi >= 0.0:
            # Crack tip is likely in this element.
            # Perform a simple bilinear interpolation to find X, Y where PHILSM=0 and PSILSM=0
            # For simplicity, we can do a least-squares fit or simple averaging if it's a quad/tri.
            # Here we approximate the crack tip by minimizing |PHILSM| + |PSILSM|

            # Very basic approximation: weighted average based on 1 / (|PHILSM| + |PSILSM| + 1e-6)
            tip_x = 0.0
            tip_y = 0.0
            tip_z = 0.0
            total_weight = 0.0

            for i, nl in enumerate(el_nodes):
                phi = el_phi[i]
                psi = el_psi[i]
                weight = 1.0 / (abs(phi) + abs(psi) + 1e-6)
                coords = node_coords[nl]
                tip_x += coords[0] * weight
                tip_y += coords[1] * weight
                tip_z += coords[2] * weight
                total_weight += weight

            tip_x /= total_weight
            tip_y /= total_weight
            tip_z /= total_weight

            crack_tips.append((tip_x, tip_y, tip_z))

    if crack_tips:
        print("Estimated crack tip coordinates:")
        for i, tip in enumerate(crack_tips):
            print("Tip %d: X = %f, Y = %f, Z = %f" % (i+1, tip[0], tip[1], tip[2]))

        with open("crack_tips.txt", "w") as f:
            f.write("Tip, X, Y, Z\n")
            for i, tip in enumerate(crack_tips):
                f.write("%d, %f, %f, %f\n" % (i+1, tip[0], tip[1], tip[2]))
    else:
        print("No crack tip found in the extracted frame.")

    odb.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: abaqus python extract_crack_tip.py <path_to_odb> [instance_name]")
        sys.exit(1)

    odb_path = sys.argv[1]
    instance_name = sys.argv[2] if len(sys.argv) > 2 else None

    extract_data_and_calculate_tip(odb_path, instance_name=instance_name)
