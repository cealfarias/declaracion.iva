import re

with open('backup_dashboard.jsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "const [activeTabs" in line:
        new_lines.append(line)
        new_lines.append("  const [activeWizardTab, setActiveWizardTab] = useState('subir_detalle');\n")
    elif "const renderResumen" in line:
        break
    else:
        new_lines.append(line)

prefix = "".join(new_lines)

with open('rewrite_logic.txt', 'r', encoding='utf-8') as f:
    append_logic = f.read()

with open('src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(prefix + append_logic)

print("Done")
