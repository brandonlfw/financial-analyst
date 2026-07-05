import plotly.graph_objects as go

CATEGORICAL_COLORS = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
DEFAULT_HIDDEN_CATEGORIES = ["Withdrawal"]


def build_category_pie_chart(breakdown, theme_type):
    """
    Builds a pie chart of spending by category from the dict returned by
    rbc_analysis.categorize_spending(). Folds the smallest categories into
    'Other' if there are more than there are fixed colour slots for.
    """
    items = sorted(breakdown.items(), key=lambda kv: -kv[1])

    if len(items) > len(CATEGORICAL_COLORS):
        cutoff = len(CATEGORICAL_COLORS) - 1
        other_amount = next((amount for label, amount in items if label == "Other"), 0)
        rest = [kv for kv in items if kv[0] != "Other"]
        head, tail = rest[:cutoff], rest[cutoff:]
        other_total = sum(amount for _, amount in tail) + other_amount
        items = sorted(head + [("Other", other_total)], key=lambda kv: -kv[1])

    labels, values = zip(*items)
    surface = "#1a1a19" if theme_type == "dark" else "#fcfcfb"
    text_color = "#ffffff" if theme_type == "dark" else "#0b0b0b"

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=CATEGORICAL_COLORS[:len(labels)], line=dict(color=surface, width=2)),
        textinfo="percent",
        textposition="inside",
        sort=False,
        hovertemplate="%{label}<br>$%{value:,.2f}<extra></extra>",
    )])
    hidden_labels = [label for label in DEFAULT_HIDDEN_CATEGORIES if label in labels]

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=text_color),
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
        margin=dict(l=0, r=0, t=10, b=10),
        hiddenlabels=hidden_labels,
    )
    return fig
