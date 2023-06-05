# MitarbeiterStatisik des UKW / Radiologie ausgewertet und visualisiert
# Leistungen sind jeweils nur einer BLAEK-Kategorie zugeordnet
# Die Zuordnung stammt von mir und ist nicht offiziell
# Die Zuordnung muss verbessert werden weil nicht 1 zu 1 möglich
# ––> siehe Dokument blaek_map.xlsx
# Mai und Juni 2023 hendel_r@ukw.de
# lokal starten mit: streamlit run blaek_stats.py
# –––––– need to fix –––––––
# 5.6.2023 UserWarning: The DataFrame has column names of mixed type. They will be converted to strings and not roundtrip correctly.
# todo:
# – fix error
# – improve mapping
# – make pdf export

import streamlit as st
import pandas as pd
import plotly.express as px
from plotly_calplot import calplot


def prepare_table(df: pd.DataFrame):
    # forward fill empty data
    df = df.fillna(method="ffill")

    # define new columns
    df["Abteilung"] = df["OEKEY"].str[3:5]
    df["Gerät"] = df["OEKEY"].str[:2]
    # df["Gesamt"] = "Gesamt"

    df["DokDatum"] = pd.to_datetime(df["DokDatum"], dayfirst=True)
    df["Date"] = pd.to_datetime(
        df["DokDatum"]
    ).dt.date  # seems redundant, need to revisit

    # add some more helper columns
    df["DokYear"] = df["DokDatum"].dt.year.astype(int)
    df["DokMonth"] = df["DokDatum"].dt.month.astype(int)
    df["DayName"] = df["DokDatum"].dt.day_name()

    # map to blaek categories
    bm = pd.read_excel("blaek_map.xlsx")
    bm.fillna("nicht definiert", inplace=True)

    df = pd.merge(df, bm, left_on="Leistung", right_on="ukw")

    return df


def make_blaektable(df: pd.DataFrame):
    pt = pd.pivot_table(
        df[df.IND2 == 1],
        index=["blaek"],
        columns="DokYear",
        values="IND2",
        aggfunc="count",
    )
    pt["Gesamt"] = pt.sum(axis=1)
    pt.fillna(0, inplace=True)

    return pt.astype(int)


def n_leistungen_n_dokumente(df: pd.DataFrame):
    n_leistungen = len(df)
    n_dokumente = len(df[df["IND2"] == 1])

    return n_leistungen, n_dokumente


def query_DataFrame(df: pd.DataFrame, query: str):
    df_query = df[df["Leistung"].str.contains(query, case=False)]
    n_results = len(df_query)

    return df_query, n_results


def make_sunburst(df: pd.DataFrame, typ=None):
    if typ == "Dokumente":
        df = df[df["IND2"] == 1]
        our_path = [px.Constant("Gesamt"), "Gerät", "Leistung"]
    elif typ == "blaek":
        our_path = [px.Constant("Gesamt"), "blaek", "Leistung"]
    else:  # default to Leistungen
        df = df[df["Leistung"].str.contains("MPR") == False]
        our_path = [px.Constant("Gesamt"), "Gerät", "Leistung"]

    fig = px.sunburst(
        df,
        width=1000,
        height=1000,
        path=our_path,
    )

    fig.update_traces(
        textinfo="label + value"
    )  # same as fig.data[0].textinfo = 'label + value'
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))

    return fig


def make_yeartable(df: pd.DataFrame, typ="Leistung"):
    if typ == "Dokumente":
        df = df[df["IND2"] == 1]
    elif typ == "Leistung":
        df = df[df["Leistung"].str.contains("MPR") == False]

    df = df.pivot_table(
        index="Gerät", columns="DokYear", aggfunc="count", fill_value=0
    )["IND1"]

    return df.astype(int)


def make_calplot(df: pd.DataFrame):
    df = df.set_index("DokDatum").resample("D").count()
    df.reset_index(inplace=True)
    # plt.figure(figsize=(20, 10))
    fig = calplot(
        df,
        x="DokDatum",
        y="Leistung",
        years_title=True,
        dark_theme=False,
    )

    return fig


# PAGE STARTS HERE
st.set_page_config(layout="wide")

st.markdown("# blaek 🐑 ")

file_upload = st.file_uploader("Mitarbeiter Statistik")


if file_upload is not None:
    try:
        df = pd.read_excel(
            file_upload,
            header=9,  # magic number 9 is row with headers
            usecols=["Leistung", "OEKEY", "IND1", "IND2", "DokDatum"],
        )
    except Exception:
        df = pd.DataFrame({"Test": "failed"})
        print(Exception)

    df = prepare_table(df)

    n_leist, n_doks = n_leistungen_n_dokumente(df)
    st.markdown(
        f"Insgesamt {n_leist} Leistungen in {n_doks} Dokumenten. Zwischen {df.DokDatum.min().date()} und {df.DokDatum.max().date()}"
    )

    # BLAEK
    st.markdown("## Facharzt?")
    df_blaek = make_blaektable(df)
    st.table(df_blaek)

    sun = make_sunburst(df, typ="blaek")
    st.plotly_chart(sun, use_container_width=True)

    # DETAILS
    st.markdown("# Details")
    st.markdown("## Suchen")
    suche = st.text_input(
        "Hier Begriff eintippen und Enter drücken um in den Leistungen zu suchen. Schränkt die nachfolgenden Leistungen und Dokumente ein:"
    )
    df_query, n_results = query_DataFrame(df, suche)
    st.markdown(f"Der Suchbegriff: {suche} fand sich in {n_results} Leistungen. ")

    # LEISTUNGEN
    st.markdown("### Leistungen")
    st.markdown("ohne MIP/MPR")
    sun = make_sunburst(df_query, typ="Leistungen")
    st.plotly_chart(sun, use_container_width=True)

    st.markdown("Anzahl der Leistungen nach Modalität und Jahr")
    st.table(make_yeartable(df, "Leistung"))

    # DOKUMENTE
    st.markdown("### Dokumente")
    sun = make_sunburst(df_query, typ="Dokumente")
    st.plotly_chart(sun, use_container_width=True)

    st.markdown("Anzahl der Dokumente nach Modalität und Jahr")
    st.table(make_yeartable(df, "Dokumente"))

    # KALENDER
    st.markdown("# Kalender")
    st.markdown(
        "Sämtliche Leistungen (nicht Dokumente). Wird nicht durch Suche eingeschränkt."
    )
    cal = make_calplot(df)
    st.plotly_chart(cal, use_container_width=True)
