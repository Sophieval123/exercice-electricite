from pathlib import Path

import pandas as pd
import streamlit as st

DOSSIER = Path(__file__).parent / "donnees"

st.set_page_config(page_title="L'électricité dans 12 quartiers", page_icon="⚡", layout="wide")

st.title("L'électricité dans 12 quartiers")
st.caption("Relevés mensuels de janvier 2024 à décembre 2025. Données fictives.")


# --- Étape 2 : lire le fichier propre (écrit par le notebook), une seule fois ---
@st.cache_data
def charger():
    return pd.read_csv(DOSSIER / "consommation_propre.csv")


df = charger()

st.write(
    "Une compagnie d'électricité suit 12 quartiers de Port-au-Prince, Delmas, "
    "Pétion-Ville et Cap-Haïtien, mois par mois, en 2024 et 2025."
)
st.write("Le directeur veut savoir : **la consommation suit-elle la chaleur, ou les heures de courant ?**")


# --- Étape 3 : deux filtres dans la barre latérale ---
toutes_communes = sorted(df["commune"].unique())
communes = st.sidebar.multiselect("Communes", toutes_communes, default=toutes_communes)

annees = sorted(df["annee"].unique(), reverse=True)  # 2025 en premier, donc par défaut
annee = st.sidebar.selectbox("Année", annees)

if not communes:
    st.warning("Choisissez au moins une commune dans la barre latérale.")
    st.stop()

choix = df[df["commune"].isin(communes)]       # communes choisies, les deux années
filtre = choix[choix["annee"] == annee]        # communes choisies, année choisie


# --- Étape 4 : trois indicateurs côte à côte ---
col1, col2, col3 = st.columns(3)
col1.metric("Consommation totale", f"{filtre['kwh'].sum() / 1_000_000:.2f} millions de kWh")
col2.metric("Consommation par abonné", f"{filtre['kwh_par_abonne'].mean():.1f} kWh")
col3.metric("Heures de courant par jour", f"{filtre['heures_courant'].mean():.1f} h")


# --- Étape 5 : un onglet par question (parties 4 à 8 du notebook) ---
onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs([
    "Qui consomme le plus ?",
    "Évolution par commune",
    "Chaleur ou courant ?",
    "Coupures",
    "Relevés hors norme",
])

with onglet1:
    classement = filtre.groupby("quartier")["kwh_par_abonne"].mean().round(1).sort_values()
    st.bar_chart(classement, horizontal=True, x_label="kWh par abonné", y_label="")
    par_type = filtre.groupby("type")["kwh_par_abonne"].mean()
    phrase = f"En tête : **{classement.index[-1]}** ({classement.iloc[-1]} kWh par abonné)."
    if {"Commercial", "Résidentiel"} <= set(par_type.index):
        phrase += (f" Un abonné commercial consomme {par_type['Commercial']:.1f} kWh, "
                   f"contre {par_type['Résidentiel']:.1f} kWh pour un résidentiel.")
    st.write(phrase)

with onglet2:
    par_mois = (choix.groupby(["mois", "commune"])["kwh"].sum()
                / choix.groupby(["mois", "commune"])["abonnes"].sum()).unstack()
    st.line_chart(par_mois, x_label="Mois", y_label="kWh par abonné")
    totaux = choix.pivot_table(index="commune", columns="annee", values="kwh", aggfunc="sum")
    hausse = ((totaux[2025] / totaux[2024] - 1) * 100).sort_values(ascending=False)
    st.write(f"La plus forte hausse de 2024 à 2025 : **{hausse.index[0]}** (+{hausse.iloc[0]:.1f} %).")

with onglet3:
    residentiel = choix[choix["type"] == "Résidentiel"]
    if len(residentiel) > 1:
        st.scatter_chart(residentiel, x="heures_courant", y="kwh_par_abonne",
                         x_label="Heures de courant par jour", y_label="kWh par abonné")
        r_courant = residentiel["kwh_par_abonne"].corr(residentiel["heures_courant"])
        r_chaleur = residentiel["kwh_par_abonne"].corr(residentiel["temperature_c"])
        st.write(f"Quartiers résidentiels, 2024 et 2025 : corrélation de **{r_courant:.2f}** avec les "
                 f"heures de courant, et de **{r_chaleur:.2f}** avec la température.")
    else:
        st.info("Aucun quartier résidentiel dans les communes choisies.")

with onglet4:
    st.bar_chart(filtre.groupby("commune")["heures_courant"].median(),
                 x_label="Commune", y_label="Heures de courant (médiane)")
    moins_de_8 = filtre[filtre["heures_courant"] < 8]
    st.write(f"En {annee}, **{len(moins_de_8)}** relevé(s) sous 8 heures de courant par jour.")

with onglet5:
    top = filtre.nlargest(3, "kwh")[["mois", "quartier", "type", "kwh"]]
    st.dataframe(top, hide_index=True)
    st.write(f"La plus grosse consommation de {annee} : **{top.iloc[0]['quartier']}** "
             f"en {top.iloc[0]['mois']} ({top.iloc[0]['kwh']:,} kWh).".replace(",", " "))


# --- Étape 6 : la conclusion, puis les données filtrées ---
st.markdown("""
### Conclusion
La consommation suit **les heures de courant**, pas la chaleur : dans les quartiers résidentiels,
la consommation par abonné a une corrélation de **0.76** avec les heures de courant, contre
**-0.15** avec la température. Une corrélation ne prouve pas une cause : elle montre que les deux
varient ensemble, et d'autres facteurs peuvent jouer.
""")

with st.expander("Voir les données filtrées"):
    st.dataframe(filtre, hide_index=True)
