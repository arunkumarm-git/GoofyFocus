import os
import json
import datetime
import webbrowser
from assets import USER_DATA_DIR

# ── Design tokens (matching app.py) ──────────────────
BG_0      = "#0f0d0e"
BG_1      = "#171415"
ACCENT     = "#FB7185"
ACCENT_2   = "#A78BFA"
TEXT_HI    = "rgba(255,255,255,255)"
TEXT_MID   = "rgba(255,255,255,190)"
TEXT_LOW   = "rgba(255,255,255,120)"

def generate_dashboard(user_info: dict):
    """
    Loads session data, generates a Plotly dashboard, and opens it in the browser.
    """
    import pandas as pd
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots

    local_db = os.path.join(USER_DATA_DIR, "sessions.json")
    data = []
    
    if os.path.exists(local_db):
        with open(local_db, "r") as f:
            data = json.load(f)
    
    if not data:
        print("[dashboard] No data found to generate dashboard.")
        return False

    df = pd.DataFrame(data)
    # Convert completed_at to datetime and localize
    df['completed_at'] = pd.to_datetime(df['completed_at'])
    df['local_time'] = df['completed_at'].dt.tz_convert(None) # Assuming naive local is fine for visualization
    df['date'] = df['local_time'].dt.date
    df['hour'] = df['local_time'].dt.hour
    df['day_name'] = df['local_time'].dt.day_name()
    df['duration_min'] = df['duration_secs'] / 60

    # 1. Daily Focus Bar Chart
    daily_focus = df[df['phase'] == 'Work'].groupby('date')['duration_min'].sum().reset_index()
    fig_daily = px.bar(
        daily_focus, x='date', y='duration_min',
        title="Daily Focus Time (min)",
        template="plotly_dark",
        color_discrete_sequence=[ACCENT]
    )
    fig_daily.update_layout(
        plot_bgcolor=BG_0, paper_bgcolor=BG_0,
        font_color=TEXT_HI, title_font_family="DM Sans"
    )

    # 2. Phase Breakdown Donut Chart
    phase_sum = df.groupby('phase')['duration_min'].sum().reset_index()
    fig_phase = px.pie(
        phase_sum, values='duration_min', names='phase',
        hole=0.5, title="Time Distribution by Phase",
        template="plotly_dark",
        color_discrete_sequence=[ACCENT, ACCENT_2, "#818cf8"]
    )
    fig_phase.update_layout(
        plot_bgcolor=BG_0, paper_bgcolor=BG_0,
        font_color=TEXT_HI, title_font_family="DM Sans"
    )

    # 3. Activity Heatmap (Hour vs Day)
    heatmap_data = df.groupby(['day_name', 'hour'])['duration_min'].sum().unstack(fill_value=0)
    # Reorder days
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = heatmap_data.reindex(days_order)
    
    fig_heatmap = px.imshow(
        heatmap_data,
        labels=dict(x="Hour of Day", y="Day of Week", color="Minutes"),
        x=heatmap_data.columns,
        y=heatmap_data.index,
        title="Focus Intensity Heatmap",
        template="plotly_dark",
        color_continuous_scale=[BG_1, ACCENT]
    )
    fig_heatmap.update_layout(
        plot_bgcolor=BG_0, paper_bgcolor=BG_0,
        font_color=TEXT_HI, title_font_family="DM Sans"
    )

    # 4. Streak Tracking Line Chart (Cumulative focus over time)
    df_sorted = df[df['phase'] == 'Work'].sort_values('local_time')
    df_sorted['cumulative_min'] = df_sorted['duration_min'].cumsum()
    
    fig_streak = px.line(
        df_sorted, x='local_time', y='cumulative_min',
        title="Cumulative Focus Progress",
        template="plotly_dark",
        color_discrete_sequence=[ACCENT]
    )
    fig_streak.update_layout(
        plot_bgcolor=BG_0, paper_bgcolor=BG_0,
        font_color=TEXT_HI, title_font_family="DM Sans"
    )

    # Combine into a single HTML
    output_path = os.path.join(USER_DATA_DIR, "focus_dashboard.html")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"""
        <html>
        <head>
            <title>Goofy Focus Dashboard</title>
            <style>
                body {{ background-color: {BG_0}; color: {TEXT_HI}; font-family: 'DM Sans', sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: {ACCENT}; text-align: center; }}
                .container {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }}
                .chart {{ width: 45%; min-width: 400px; background: {BG_1}; padding: 10px; border-radius: 15px; border: 1px solid rgba(251, 113, 133, 40); }}
                @media (max-width: 900px) {{ .chart {{ width: 95%; }} }}
            </style>
        </head>
        <body>
            <h1>Focus Dashboard</h1>
            <div class="container">
                <div class="chart">{fig_daily.to_html(full_html=False, include_plotlyjs='cdn')}</div>
                <div class="chart">{fig_phase.to_html(full_html=False, include_plotlyjs=False)}</div>
                <div class="chart">{fig_heatmap.to_html(full_html=False, include_plotlyjs=False)}</div>
                <div class="chart">{fig_streak.to_html(full_html=False, include_plotlyjs=False)}</div>
            </div>
        </body>
        </html>
        """)

    webbrowser.open(f"file://{os.path.abspath(output_path)}")
    return True
