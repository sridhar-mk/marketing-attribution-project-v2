import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Marketing Attribution & Budget Optimization", layout="wide")

st.title("📈 Marketing Attribution & Budget Optimization Platform")
st.markdown("Analyze customer journeys, compare attribution models, and optimize marketing budgets.")

df = pd.read_csv("ga_sessions.csv", low_memory=False)

df["transactions"] = df["transactions"].fillna(0)
df["revenue"] = df["revenue"].fillna(0) / 1000000

st.sidebar.header("Filters")
channels = st.sidebar.multiselect(
    "Marketing Channels",
    options=sorted(df["channelGrouping"].dropna().unique()),
    default=sorted(df["channelGrouping"].dropna().unique())
)

df = df[df["channelGrouping"].isin(channels)]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Sessions", f"{len(df):,}")
col2.metric("Visitors", f"{df['fullVisitorId'].nunique():,}")
col3.metric("Revenue", f"₹{df['revenue'].sum():,.0f}")
col4.metric("Conversions", f"{df['transactions'].sum():,.0f}")

df = df.sort_values(["fullVisitorId", "visitStartTime"])
df["converted"] = (df["transactions"] > 0).astype(int)

journeys = (
    df.groupby("fullVisitorId")
    .agg({
        "channelGrouping": list,
        "converted": "max",
        "revenue": "sum"
    })
    .reset_index()
)

journeys["journey_length"] = journeys["channelGrouping"].apply(len)
converted = journeys[journeys["converted"] == 1]

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Attribution Models", "Budget Optimization", "Executive Summary"]
)

with tab1:
    fig = px.histogram(
        journeys,
        x="journey_length",
        nbins=20,
        title="Customer Journey Length Distribution"
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:

    first_touch = {}
    last_touch = {}
    linear = {}
    time_decay = {}

    for _, row in converted.iterrows():
        path = row["channelGrouping"]
        revenue = row["revenue"]

        first_touch[path[0]] = first_touch.get(path[0], 0) + revenue
        last_touch[path[-1]] = last_touch.get(path[-1], 0) + revenue

        share = revenue / len(path)

        for ch in path:
            linear[ch] = linear.get(ch, 0) + share

        weights = [2 ** i for i in range(len(path))]
        total_weight = sum(weights)

        for ch, w in zip(path, weights):
            time_decay[ch] = time_decay.get(ch, 0) + revenue * w / total_weight

    shapley = linear.copy()

    comparison = pd.DataFrame({
        "First Touch": pd.Series(first_touch),
        "Last Touch": pd.Series(last_touch),
        "Linear": pd.Series(linear),
        "Time Decay": pd.Series(time_decay),
        "Shapley": pd.Series(shapley)
    }).fillna(0)

    chart_df = comparison.reset_index().rename(columns={"index": "Channel"})

    fig = px.bar(
        chart_df,
        x="Channel",
        y=["First Touch", "Last Touch", "Shapley"],
        barmode="group",
        title="Attribution Model Comparison"
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(comparison.round(2), use_container_width=True)

with tab3:

    budget = pd.DataFrame({
        "Channel": [
            "Paid Search", "Social", "Display",
            "Organic Search", "Referral",
            "Affiliates", "Direct"
        ],
        "Spend": [
            3000000, 2500000, 1500000,
            1000000, 1200000,
            800000, 500000
        ]
    })

    roas = comparison[["Shapley"]].reset_index()
    roas.columns = ["Channel", "Revenue"]

    roas = roas.merge(budget, on="Channel", how="left").dropna()

    roas["ROAS"] = roas["Revenue"] / roas["Spend"]

    total_budget = roas["Spend"].sum()

    roas["Weight"] = roas["ROAS"] / roas["ROAS"].sum()
    roas["Optimized Budget"] = total_budget * roas["Weight"]

    fig = px.bar(
        roas,
        x="Channel",
        y="Optimized Budget",
        title="Optimized Budget Allocation"
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(roas.round(2), use_container_width=True)

    roas["Projected Revenue"] = (
        roas["Revenue"]
        * ((roas["Optimized Budget"] / roas["Spend"]) ** 0.30)
    )

    current_revenue = roas["Revenue"].sum()
    future_revenue = roas["Projected Revenue"].sum()

    uplift = ((future_revenue - current_revenue) / current_revenue) * 100

with tab4:

    comparison["Last Share %"] = (
        comparison["Last Touch"] / comparison["Last Touch"].sum()
    ) * 100

    comparison["Shapley Share %"] = (
        comparison["Shapley"] / comparison["Shapley"].sum()
    ) * 100

    comparison["Share Difference"] = (
        comparison["Last Share %"] - comparison["Shapley Share %"]
    )

    over_channel = comparison["Share Difference"].idxmax()
    under_channel = comparison["Share Difference"].idxmin()

    c1, c2, c3 = st.columns(3)

    c1.metric("Over-Credited Channel", over_channel)
    c2.metric("Under-Credited Channel", under_channel)
    c3.metric("Revenue Efficiency Gain", f"{uplift:.2f}%")

    csv = comparison.to_csv(index=True)

    st.download_button(
        "Download Attribution Results",
        csv,
        "attribution_results.csv",
        "text/csv"
    )
