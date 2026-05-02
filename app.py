import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Condominio PRO",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- CSS OTTIMIZZATO ANCHE PER MOBILE (S26 Ultra) ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Ottimizzazione font per mobile */
    @media (max-width: 600px) {
        .stMarkdown h1 {
            font-size: 1.8rem !important;
        }
        .stButton button {
            width: 100%;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- COSTANTI DATABASE ---
DB_CONDOMINI = "anagrafica_condomini.csv"
DB_PREVENTIVO = "preventivo_annuale.csv"
MESI_ANNO = 12

# --- FUNZIONI CARICAMENTO DATI ---
@st.cache_data
def carica_condomini():
    if os.path.exists(DB_CONDOMINI):
        try:
            return pd.read_csv(DB_CONDOMINI)
        except Exception as e:
            st.error(f"Errore lettura anagrafica: {e}")
            return get_condomini_default()
    return get_condomini_default()

def get_condomini_default():
    """Dataset di esempio se il file non esiste"""
    return pd.DataFrame([
        {"ID": "Apt 1", "Prop": 200.0, "Scale": 150.0, "Risc": 180.0},
        {"ID": "Apt 2", "Prop": 300.0, "Scale": 250.0, "Risc": 320.0},
        {"ID": "Apt 3", "Prop": 500.0, "Scale": 600.0, "Risc": 500.0},
    ])

@st.cache_data
def carica_preventivo():
    if os.path.exists(DB_PREVENTIVO):
        try:
            return pd.read_csv(DB_PREVENTIVO).iloc[0].to_dict()
        except Exception as e:
            st.error(f"Errore lettura preventivo: {e}")
            return get_preventivo_default()
    return get_preventivo_default()

def get_preventivo_default():
    """Dataset di esempio per il preventivo"""
    return {
        "cancelleria": 100.0, "varie": 200.0, "passo": 150.0, "acqua": 800.0,
        "luce": 500.0, "pulizia": 1200.0, "caldaia": 300.0, "gasolio": 2500.0
    }

def salva_preventivo(dati):
    """Salva il preventivo e invalida la cache"""
    pd.DataFrame([dati]).to_csv(DB_PREVENTIVO, index=False)
    st.cache_data.clear()

def salva_condomini(df):
    """Salva gli alloggi e invalida la cache"""
    df.to_csv(DB_CONDOMINI, index=False)
    st.cache_data.clear()

# --- VALIDAZIONE DATI ---
def valida_preventivo(dati):
    """Valida che tutti i valori siano positivi"""
    for chiave, valore in dati.items():
        if valore < 0:
            return False, f"Errore: {chiave} non può essere negativo"
    return True, "OK"

def valida_unita(nome, prop, scale, risc):
    """Valida i dati della nuova unità"""
    if not nome.strip():
        return False, "Il nome/ID dell'alloggio è obbligatorio"
    if prop < 0 or scale < 0 or risc < 0:
        return False, "I millesimi non possono essere negativi"
    return True, "OK"

# --- LOGICA DI CALCOLO ---
class CalcoloManager:
    def __init__(self, preventivo):
        self.p = preventivo
    
    @property
    def tot_a(self): 
        """Totale Tabella A - Proprietà"""
        return sum([self.p['cancelleria'], self.p['varie'], self.p['passo'], self.p['acqua']])
    
    @property
    def tot_b(self): 
        """Totale Tabella B - Scale/Luce"""
        return sum([self.p['luce'], self.p['pulizia']])
    
    @property
    def tot_d(self): 
        """Totale Tabella D - Riscaldamento"""
        return sum([self.p['caldaia'], self.p['gasolio']])
    
    @property
    def tot_annuale(self):
        """Totale budget annuale"""
        return self.tot_a + self.tot_b + self.tot_d
    
    def calcola_rate(self, df_c):
        """
        Calcola le rate mensili per ogni unità.
        Formula CORRETTA: (totale / 12 mesi) * (millesimi / 1000)
        """
        res = []
        for _, r in df_c.iterrows():
            # Calcolo mensile basato sui millesimi (corretta normalizzazione)
            ma = (self.tot_a / 12) * (r['Prop'] / 1000)
            mb = (self.tot_b / 12) * (r['Scale'] / 1000)
            md = (self.tot_d / 12) * (r['Risc'] / 1000)
            res.append({
                'Unità': r['ID'],
                'Quota A (€)': round(ma, 2),
                'Quota B (€)': round(mb, 2),
                'Quota D (€)': round(md, 2),
                'TOTALE MENSILE (€)': round(ma + mb + md, 2)
            })
        return pd.DataFrame(res)
    
    def calcola_annuale_per_unita(self, df_c):
        """Calcola il totale annuale per ogni unità"""
        df_rate = self.calcola_rate(df_c)
        df_rate['TOTALE ANNUALE (€)'] = df_rate['TOTALE MENSILE (€)'] * 12
        return df_rate[['Unità', 'TOTALE ANNUALE (€)']].copy()

# --- PAGINE ---
def pagina_dashboard():
    st.title("🏠 Prospetto Mensilità")
    df_c = carica_condomini()
    p = carica_preventivo()
    mgr = CalcoloManager(p)
    
    # KPI veloci
    c1, c2, c3 = st.columns(3)
    c1.metric("Budget Annuale", f"€ {mgr.tot_annuale:,.2f}")
    c2.metric("Unità Totali", len(df_c))
    c3.metric("Rata Media Mensile", f"€ {mgr.calcola_rate(df_c)['TOTALE MENSILE (€)'].mean():.2f}")

    st.subheader("Tabella Rate Mensili")
    df_res = mgr.calcola_rate(df_c)
    st.dataframe(df_res, use_container_width=True, hide_index=True)

    # Grafico per cellulare - Rata mensile per alloggio
    fig = px.bar(
        df_res, 
        x='Unità', 
        y='TOTALE MENSILE (€)', 
        title="Rata Mensile per Alloggio",
        color='TOTALE MENSILE (€)',
        color_continuous_scale="Blues"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Breakdown per categoria
    st.subheader("Breakdown Spese per Categoria")
    c1, c2, c3 = st.columns(3)
    c1.metric("Categoria A (Proprietà)", f"€ {mgr.tot_a:,.2f}")
    c2.metric("Categoria B (Scale/Luce)", f"€ {mgr.tot_b:,.2f}")
    c3.metric("Categoria D (Riscaldamento)", f"€ {mgr.tot_d:,.2f}")
    
    # Grafico torta spese annuali
    fig_pie = go.Figure(data=[go.Pie(
        labels=['Proprietà (A)', 'Scale/Luce (B)', 'Riscaldamento (D)'],
        values=[mgr.tot_a, mgr.tot_b, mgr.tot_d],
        marker=dict(colors=['#636EFA', '#EF553B', '#00CC96'])
    )])
    fig_pie.update_layout(title="Distribuzione Spese Annuali")
    st.plotly_chart(fig_pie, use_container_width=True)

def pagina_preventivo():
    st.title("📊 Gestione Spese")
    p = carica_preventivo()
    
    with st.form("spese"):
        st.subheader("Tabella A - Proprietà")
        c1, c2 = st.columns(2)
        v1 = c1.number_input("Cancelleria", value=float(p['cancelleria']), min_value=0.0)
        v2 = c2.number_input("Varie", value=float(p['varie']), min_value=0.0)
        v3 = c1.number_input("Passo Carrabile", value=float(p['passo']), min_value=0.0)
        v4 = c2.number_input("Acqua", value=float(p['acqua']), min_value=0.0)
        
        st.subheader("Tabella B - Scale/Luce")
        v5 = c1.number_input("Luce", value=float(p['luce']), min_value=0.0)
        v6 = c2.number_input("Pulizia", value=float(p['pulizia']), min_value=0.0)
        
        st.subheader("Tabella D - Riscaldamento")
        v7 = c1.number_input("Caldaia", value=float(p['caldaia']), min_value=0.0)
        v8 = c2.number_input("Gasolio", value=float(p['gasolio']), min_value=0.0)
        
        if st.form_submit_button("Salva e Aggiorna"):
            new_preventivo = {
                "cancelleria": v1, "varie": v2, "passo": v3, "acqua": v4,
                "luce": v5, "pulizia": v6, "caldaia": v7, "gasolio": v8
            }
            
            valido, msg = valida_preventivo(new_preventivo)
            if valido:
                salva_preventivo(new_preventivo)
                st.success("✅ Dati aggiornati!")
                st.rerun()
            else:
                st.error(f"❌ {msg}")
    
    # Riepilogo spese
    st.subheader("Riepilogo Spese Annuali")
    mgr = CalcoloManager(carica_preventivo())
    c1, c2, c3 = st.columns(3)
    c1.metric("Totale A", f"€ {mgr.tot_a:,.2f}")
    c2.metric("Totale B", f"€ {mgr.tot_b:,.2f}")
    c3.metric("Totale D", f"€ {mgr.tot_d:,.2f}")
    st.metric("TOTALE ANNUALE", f"€ {mgr.tot_annuale:,.2f}")

def pagina_unita():
    st.title("👥 Anagrafica Unità")
    df_c = carica_condomini()
    
    # Mostra numero di unità e totale millesimi
    col1, col2, col3 = st.columns(3)
    col1.metric("Unità Totali", len(df_c))
    col2.metric("Millesimi Proprietà (tot)", f"{df_c['Prop'].sum():.0f}")
    col3.metric("Millesimi Riscaldamento (tot)", f"{df_c['Risc'].sum():.0f}")
    
    st.dataframe(df_c, use_container_width=True, hide_index=True)
    
    # AGGIUNGI NUOVA UNITÀ
    with st.expander("➕ Aggiungi Nuova Unità"):
        new_id = st.text_input("Nome/ID Alloggio", placeholder="Es: Apt 4, Unità A, etc.")
        c1, c2, c3 = st.columns(3)
        p = c1.number_input("Mill. Proprietà", min_value=0.0, max_value=1000.0, value=0.0)
        s = c2.number_input("Mill. Scale", min_value=0.0, max_value=1000.0, value=0.0)
        r = c3.number_input("Mill. Riscaldamento", min_value=0.0, max_value=1000.0, value=0.0)
        
        if st.button("Inserisci Unità"):
            valido, msg = valida_unita(new_id, p, s, r)
            if valido:
                # Controlla che l'ID non esista già
                if new_id in df_c['ID'].values:
                    st.error("❌ Un'unità con questo ID esiste già!")
                else:
                    new_df = pd.concat([
                        df_c, 
                        pd.DataFrame([{"ID": new_id, "Prop": p, "Scale": s, "Risc": r}])
                    ], ignore_index=True)
                    salva_condomini(new_df)
                    st.success(f"✅ Unità '{new_id}' aggiunta con successo!")
                    st.rerun()
            else:
                st.error(f"❌ {msg}")
    
    # MODIFICA/ELIMINA UNITÀ
    with st.expander("✏️ Modifica Unità Esistente"):
        if len(df_c) > 0:
            unita_sel = st.selectbox("Seleziona unità", df_c['ID'].values, key="edit_select")
            unita_data = df_c[df_c['ID'] == unita_sel].iloc[0]
            
            c1, c2, c3 = st.columns(3)
            prop_new = c1.number_input("Mill. Proprietà", value=float(unita_data['Prop']), min_value=0.0)
            scale_new = c2.number_input("Mill. Scale", value=float(unita_data['Scale']), min_value=0.0)
            risc_new = c3.number_input("Mill. Riscaldamento", value=float(unita_data['Risc']), min_value=0.0)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Salva Modifiche"):
                    df_c.loc[df_c['ID'] == unita_sel, ['Prop', 'Scale', 'Risc']] = [prop_new, scale_new, risc_new]
                    salva_condomini(df_c)
                    st.success(f"✅ Unità '{unita_sel}' modificata!")
                    st.rerun()
            
            with col2:
                if st.button("Elimina Unità", type="secondary"):
                    df_c = df_c[df_c['ID'] != unita_sel]
                    salva_condomini(df_c)
                    st.success(f"✅ Unità '{unita_sel}' eliminata!")
                    st.rerun()
        else:
            st.info("ℹ️ Nessuna unità disponibile")

# --- NAVIGAZIONE ---
def main():
    st.sidebar.title("🏢 Condominio PRO")
    scelta = st.sidebar.selectbox(
        "Seleziona Pagina",
        ["Dashboard", "Preventivo", "Unità Abitative"]
    )
    
    if scelta == "Dashboard": 
        pagina_dashboard()
    elif scelta == "Preventivo": 
        pagina_preventivo()
    else: 
        pagina_unita()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("Condominio PRO v2.0 | Gestione Spese Condominiali")

if __name__ == "__main__":
    main()
