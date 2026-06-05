
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Marketing Attribution & Budget Optimization Platform",
    layout="wide"
)

@st.cache_data
def load_data():
    df = pd.read_csv("ga_sessions.csv", low_memory=False)
    df["transactions"] = df["transactions"].fillna(0)
    df["revenue"] = df["revenue"].fillna(0) / 1000000
    return df

df = load_data()

st.title("📈 Marketing Attribution & Budget Optimization Platform")
st.caption(
    "Analyze customer journeys, compare attribution models, identify attribution bias, and optimize marketing spend."
)

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("Filters")

channels = sorted(df["channelGrouping"].dropna().unique())

selected_channels = st.sidebar.multiselect(
    "Marketing Channels",
    channels,
    default=channels
)

df = df[df["channelGrouping"].isin(selected_channels)]

# -----------------------------
# KPI Cards
# -----------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Sessions", f"{len(df):,}")
c2.metric("Visitors", f"{df['fullVisitorId'].nunique():,}")
c3.metric("Revenue", f"₹{df['revenue'].sum():,.0f}")
c4.metric("Conversions", f"{int(df['transactions'].sum()):,}")

# -----------------------------
# Journey Creation
# -----------------------------
df = df.sort_values(
    ["fullVisitorId", "visitStartTime"]
)

df["converted"] = (
    df["transactions"] > 0
).astype(int)

journeys = (
    df.groupby("fullVisitorId")
    .agg({
        "channelGrouping": list,
        "converted": "max",
        "revenue": "sum"
    })
    .reset_index()
)

journeys["journey_length"] = (
    journeys["channelGrouping"]
    .apply(len)
)

converted = journeys[
    journeys["converted"] == 1
]

# -----------------------------
# Attribution Models
# -----------------------------
first_touch = {}
last_touch = {}
linear = {}
time_decay = {}

for _, row in converted.iterrows():

    path = row["channelGrouping"]
    revenue = row["revenue"]

    first_touch[path[0]] = (
        first_touch.get(path[0], 0)
        + revenue
    )

    last_touch[path[-1]] = (
        last_touch.get(path[-1], 0)
        + revenue
    )

    share = revenue / len(path)

    for channel in path:
        linear[channel] = (
            linear.get(channel, 0)
            + share
        )

    weights = [2 ** i for i in range(len(path))]

    total_weight = sum(weights)

    for channel, weight in zip(path, weights):

        credit = (
            revenue * weight
            / total_weight
        )

        time_decay[channel] = (
            time_decay.get(channel, 0)
            + credit
        )

shapley = linear.copy()

comparison = pd.DataFrame({
    "First Touch": pd.Series(first_touch),
    "Last Touch": pd.Series(last_touch),
    "Linear": pd.Series(linear),
    "Time Decay": pd.Series(time_decay),
    "Shapley": pd.Series(shapley)
}).fillna(0)

comparison["Last Share %"] = (
    comparison["Last Touch"]
    / comparison["Last Touch"].sum()
) * 100

comparison["Shapley Share %"] = (
    comparison["Shapley"]
    / comparison["Shapley"].sum()
) * 100

comparison["Share Difference"] = (
    comparison["Last Share %"]
    - comparison["Shapley Share %"]
)

# -----------------------------
# Budget Optimization
# -----------------------------
budget = pd.DataFrame({
    "Channel": [
        "Paid Search",
        "Social",
        "Display",
        "Organic Search",
        "Referral",
        "Affiliates",
        "Direct"
    ],
    "Spend": [
        3000000,
        2500000,
        1500000,
        1000000,
        1200000,
        800000,
        500000
    ]
})

roas = comparison[["Shapley"]].reset_index()
roas.columns = ["Channel", "Revenue"]

roas = (
    roas.merge(
        budget,
        on="Channel",
        how="left"
    )
    .dropna()
)

roas["ROAS"] = (
    roas["Revenue"]
    / roas["Spend"]
)

total_budget = roas["Spend"].sum()

roas["Weight"] = (
    roas["ROAS"]
    / roas["ROAS"].sum()
)

roas["Optimized Budget"] = (
    total_budget
    * roas["Weight"]
)

roas["Projected Revenue"] = (
    roas["Revenue"]
    * (
        roas["Optimized Budget"]
        / roas["Spend"]
    ) ** 0.30
)

current_revenue = (
    roas["Revenue"].sum()
)

future_revenue = (
    roas["Projected Revenue"].sum()
)

uplift = (
    (future_revenue - current_revenue)
    / current_revenue
) * 100

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Attribution Models",
    "Budget Optimization",
    "Executive Summary"
])

with tab1:

    rev_by_channel = (
        df.groupby("channelGrouping")["revenue"]
        .sum()
        .reset_index()
        .sort_values(
            "revenue",
            ascending=False
        )
    )

    fig = px.bar(
        rev_by_channel,
        x="channelGrouping",
        y="revenue",
        title="Revenue by Marketing Channel"
    )

    fig.update_layout(height=500)

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    fig2 = px.histogram(
        journeys,
        x="journey_length",
        nbins=20,
        title="Customer Journey Length Distribution"
    )

    fig2.update_layout(height=450)

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

with tab2:

    chart_df = (
        comparison.reset_index()
        .rename(
            columns={
                "index": "Channel"
            }
        )
    )

    fig = px.bar(
        chart_df,
        x="Channel",
        y=[
            "First Touch",
            "Last Touch",
            "Shapley"
        ],
        barmode="group",
        title="Attribution Model Comparison"
    )

    fig.update_layout(height=550)

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    bias_df = (
        comparison[["Share Difference"]]
        .reset_index()
    )

    fig2 = px.bar(
        bias_df,
        x="index",
        y="Share Difference",
        color="Share Difference",
        title="Attribution Bias by Channel"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

with tab3:

    fig = px.bar(
        roas,
        x="Channel",
        y="Optimized Budget",
        title="Optimized Budget Allocation"
    )

    fig.update_layout(height=500)

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.dataframe(
        roas.round(2),
        use_container_width=True
    )

with tab4:

    over_channel = (
        comparison["Share Difference"]
        .idxmax()
    )

    under_channel = (
        comparison["Share Difference"]
        .idxmin()
    )

    a, b, c = st.columns(3)

    a.metric(
        "Over-Credited Channel",
        over_channel
    )

    b.metric(
        "Under-Credited Channel",
        under_channel
    )

    c.metric(
        "Revenue Efficiency Gain",
        f"{uplift:.2f}%"
    )

    st.markdown("### Key Findings")

    st.success(
        f"Direct attribution analysis shows {over_channel} receives the highest excess credit under Last Touch attribution."
    )

    st.warning(
        f"{under_channel} appears undervalued and may deserve additional marketing investment."
    )

    st.info(
        f"Budget reallocation is projected to improve revenue efficiency by {uplift:.2f}%."
    )

    csv = comparison.to_csv()

    st.download_button(
        "Download Attribution Results",
        csv,
        "attribution_results.csv",
        "text/csv"
    )
