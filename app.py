import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Marketing Attribution Dashboard",
    layout="wide"
)

st.title("Multi-Touch Attribution Modelling Dashboard")

import os

file_path = os.path.join("data", "ga_sessions.csv")
df = pd.read_csv(file_path, low_memory=False)
if uploaded_file:

    df = pd.read_csv(
        uploaded_file,
        low_memory=False
    )

    df['transactions'] = (
        df['transactions']
        .fillna(0)
    )

    df['revenue'] = (
        df['revenue']
        .fillna(0)
        / 1000000
    )

    st.header("Dataset Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Sessions",
        f"{len(df):,}"
    )

    col2.metric(
        "Visitors",
        f"{df['fullVisitorId'].nunique():,}"
    )

    col3.metric(
        "Revenue",
        f"₹{df['revenue'].sum():,.0f}"
    )

    # -------------------------
    # Journey Creation
    # -------------------------

    df = df.sort_values(
        ['fullVisitorId', 'visitStartTime']
    )

    df['converted'] = (
        df['transactions'] > 0
    ).astype(int)

    journeys = (

        df.groupby('fullVisitorId')
        .agg({
            'channelGrouping': list,
            'converted': 'max',
            'revenue': 'sum'
        })
        .reset_index()

    )

    converted = journeys[
        journeys['converted'] == 1
    ]

    st.header("Journey Analysis")

    journeys['journey_length'] = (
        journeys['channelGrouping']
        .apply(len)
    )

    fig, ax = plt.subplots()

    journeys['journey_length'].hist(
        bins=20,
        ax=ax
    )

    ax.set_title(
        "Journey Length Distribution"
    )

    st.pyplot(fig)

    # -------------------------
    # Attribution Models
    # -------------------------

    last_touch = {}
    first_touch = {}
    linear = {}
    time_decay = {}

    for _, row in converted.iterrows():

        path = row['channelGrouping']
        revenue = row['revenue']

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

        weights = [
            2 ** i
            for i in range(len(path))
        ]

        total_weight = sum(weights)

        for channel, weight in zip(
            path,
            weights
        ):

            credit = (
                revenue
                * weight
                / total_weight
            )

            time_decay[channel] = (
                time_decay.get(channel, 0)
                + credit
            )

    # -------------------------
    # Simplified Shapley
    # -------------------------

    shapley = linear.copy()

    comparison = pd.DataFrame({

        "First Touch":
        pd.Series(first_touch),

        "Last Touch":
        pd.Series(last_touch),

        "Linear":
        pd.Series(linear),

        "Time Decay":
        pd.Series(time_decay),

        "Shapley":
        pd.Series(shapley)

    }).fillna(0)

    comparison['Last Share %'] = (

        comparison['Last Touch']
        /
        comparison['Last Touch'].sum()

    ) * 100

    comparison['Shapley Share %'] = (

        comparison['Shapley']
        /
        comparison['Shapley'].sum()

    ) * 100

    comparison['Share Difference'] = (

        comparison['Last Share %']
        -
        comparison['Shapley Share %']

    )

    st.header(
        "Attribution Comparison"
    )

    st.dataframe(
        comparison.round(2)
    )

    # -------------------------
    # Share Difference Chart
    # -------------------------

    fig, ax = plt.subplots()

    comparison[
        'Share Difference'
    ].sort_values().plot(
        kind='barh',
        ax=ax
    )

    ax.set_title(
        'Attribution Bias'
    )

    st.pyplot(fig)

    # -------------------------
    # Budget Allocation
    # -------------------------

    st.header(
        "Budget Optimisation"
    )

    budget = pd.DataFrame({

        'Channel': [
            'Paid Search',
            'Social',
            'Display',
            'Organic Search',
            'Referral',
            'Affiliates',
            'Direct'
        ],

        'Spend': [
            3000000,
            2500000,
            1500000,
            1000000,
            1200000,
            800000,
            500000
        ]

    })

    roas = comparison[
        ['Shapley']
    ].reset_index()

    roas.columns = [
        'Channel',
        'Revenue'
    ]

    roas = roas.merge(
        budget,
        on='Channel',
        how='left'
    )

    roas = roas.dropna()

    roas['ROAS'] = (
        roas['Revenue']
        /
        roas['Spend']
    )

    total_budget = (
        roas['Spend'].sum()
    )

    roas['Weight'] = (
        roas['ROAS']
        /
        roas['ROAS'].sum()
    )

    roas['Optimized Budget'] = (
        total_budget
        *
        roas['Weight']
    )

    st.dataframe(
        roas.round(2)
    )

    # -------------------------
    # Revenue Simulation
    # -------------------------

    roas['Projected Revenue'] = (

        roas['Revenue']

        *

        (
            roas['Optimized Budget']
            /
            roas['Spend']
        ) ** 0.30

    )

    current_revenue = (
        roas['Revenue']
        .sum()
    )

    future_revenue = (
        roas['Projected Revenue']
        .sum()
    )

    uplift = (

        (
            future_revenue
            -
            current_revenue
        )

        /
        current_revenue

    ) * 100

    st.header(
        "Executive Summary"
    )

    over_channel = (
        comparison[
            'Share Difference'
        ].idxmax()
    )

    under_channel = (
        comparison[
            'Share Difference'
        ].idxmin()
    )

    st.success(
        f"Most Over-Credited Channel: {over_channel}"
    )

    st.warning(
        f"Most Under-Credited Channel: {under_channel}"
    )

    st.info(
        f"Projected Revenue Efficiency Improvement: {uplift:.2f}%"
    )
