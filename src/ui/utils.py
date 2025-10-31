def human_gb(val_kb):
    # Use decimal (1000) units for user-friendly display
    gb = int(val_kb) / 1_000_000
    if gb >= 1:
        return f"{round(gb)} GB"
    else:
        return f"{int(val_kb)//1000} MB"

def human_storage(val):
    try:
        val = int(val)
        gb = val / 1_000_000
        if gb >= 1:
            return f"{round(gb)} GB"
        mb = val / 1000
        if mb >= 1:
            return f"{int(mb)} MB"
        return f"{val} KB"
    except Exception:
        return val
