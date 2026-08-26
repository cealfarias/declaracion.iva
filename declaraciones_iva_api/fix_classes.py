import re

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix the broken classNames for the buttons
bad_class = "className={px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap }"
good_class = "className={`px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap ${loading || archivos.compras.length === 0 ? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'bg-[#004b79] hover:bg-[#00385c] text-white'}`}"
code = code.replace(bad_class, good_class)

# The FCF and CCF buttons might have evaluated other things
bad_class2 = "className={px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap }"
# Actually, let's just use regex to fix any button that looks like this
code = re.sub(
    r'className=\{px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap \}',
    r'className={`px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap ${loading ? "bg-slate-300 text-slate-500 cursor-not-allowed" : "bg-[#004b79] hover:bg-[#00385c] text-white"}`}',
    code
)

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
