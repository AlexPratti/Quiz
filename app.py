import streamlit as st
import streamlit.components.v1 as components
from docx import Document
from supabase import create_client
import random
import string
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO DA PÁGINA (MANTIDA ORIGINAL) ---
st.set_page_config(page_title="Jogo Quiz", layout="wide")

# --- 2. CONEXÃO SUPABASE (USANDO SEUS SECRETS) ---
url = st.secrets["URL_SUPABASE"]
key = st.secrets["KEY_SUPABASE"]
supabase = create_client(url, key)

# Refresh de 2s para sincronização constante entre Admin e Jogadores
st_autorefresh(interval=2000, key="sync_original_v10_final")

# --- 3. FUNÇÃO DE LEITURA DO WORD (MANTIDA ORIGINAL) ---
def parse_word_file(file):
    documento = Document(file)
    texto_extraido = []
    for paragrafo in documento.paragraphs:
        conteudo = paragrafo.text.strip()
        if conteudo != "":
            texto_extraido.append(conteudo)
    
    lista_final = []
    for i in range(0, len(texto_extraido), 2):
        if (i + 1) < len(texto_extraido):
            lista_final.append({
                "question_text_quiz": texto_extraido[i],
                "answer_text_quiz": texto_extraido[i+1]
            })
    return lista_final

# --- 4. ESTILIZAÇÃO CSS (MANTIDA ORIGINALIDADE E ALTA VISIBILIDADE) ---
st.markdown("""
    <style>
    .caixa-pergunta {
        background-color: #DDEBF7;
        padding: 40px;
        border: 4px solid #4472C4;
        text-align: center;
        font-size: 35px;
        font-weight: bold;
        color: #002060;
        border-radius: 15px;
        margin-bottom: 25px;
    }
    .display-cronometro {
        background-color: #595959;
        color: #FFFFFF;
        padding: 15px;
        font-size: 65px;
        text-align: center;
        font-weight: bold;
        width: 200px;
        margin: 20px auto;
        border-radius: 10px;
        border: 2px solid #000;
    }
    .vencedor-buzzer {
        background-color: #FFD700;
        color: #000;
        padding: 15px;
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        border: 4px solid #B8860B;
        border-radius: 15px;
        margin-top: 15px;
    }
    .contador-jogadores {
        background-color: #4472C4;
        color: white;
        padding: 10px;
        text-align: center;
        border-radius: 8px;
        font-weight: bold;
        font-size: 18px;
        margin-top: 10px;
        border: 1px solid #000;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. LÓGICA DE LOGIN E SESSÃO ---
if 'auth' not in st.session_state:
    st.session_state.auth = {'logged': False, 'role': None, 'id': None, 'nickname': None}
if 'show_players_list' not in st.session_state:
    st.session_state.show_players_list = False
if 'pool_questoes' not in st.session_state:
    st.session_state.pool_questoes = []

if not st.session_state.auth['logged']:
    st.title("🔑 Quiz: Entre e Jogue!")
    u_nome = st.text_input("Apelido")
    u_pass = st.text_input("Senha", type="password")
    
    if st.button("Entrar no Jogo"):
        if u_pass == st.secrets["ADMIN_PASSWORD"]:
            nova_pwd = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            supabase.table("game_state_quiz").update({"master_password_quiz": nova_pwd}).eq("id_quiz", 1).execute()
            supabase.table("players_quiz").delete().neq("id_quiz", 0).execute()
            st.session_state.auth = {'logged': True, 'role': 'admin', 'id': 'admin', 'nickname': 'ADMIN'}
            st.rerun()
        else:
            res = supabase.table("game_state_quiz").select("master_password_quiz").eq("id_quiz", 1).single().execute()
            if u_pass == res.data['master_password_quiz']:
                p_exec = supabase.table("players_quiz").insert({"nickname_quiz": u_nome}).execute()
                if p_exec.data:
                    st.session_state.auth = {
                        'logged': True, 
                        'role': 'player', 
                        'id': p_exec.data[0]['id_quiz'],
                        'nickname': u_nome
                    }
                    st.rerun()
            else:
                st.error("Senha incorreta!")

# --- 6. INTERFACE LOGADA ---
else:
    if st.session_state.auth['role'] == 'player':
        check_db = supabase.table("players_quiz").select("id_quiz").eq("id_quiz", st.session_state.auth['id']).execute()
        if not check_db.data:
            st.session_state.auth = {'logged': False, 'role': None, 'id': None, 'nickname': None}
            st.rerun()

    st.sidebar.title("🎮 MENU DO QUIZ")
    
    if st.sidebar.button("🚪 SAIR E ENCERRAR TUDO", use_container_width=True):
        if st.session_state.auth['role'] == 'admin':
            supabase.table("players_quiz").delete().neq("id_quiz", 0).execute()
        else:
            supabase.table("players_quiz").delete().eq("id_quiz", st.session_state.auth['id']).execute()
        st.session_state.auth = {'logged': False, 'role': None, 'id': None, 'nickname': None}
        st.rerun()

    st.sidebar.divider()

    if st.session_state.auth['role'] == 'admin':
        state = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
        st.sidebar.info(f"SENHA JOGADORES: {state['master_password_quiz']}")
        
        f_word = st.sidebar.file_uploader("Arquivo Word", type="docx")
        if f_word and st.sidebar.button("📤 CARREGAR QUESTÕES"):
            dados_word = parse_word_file(f_word)
            supabase.table("questions_quiz").delete().neq("id_quiz", 0).execute()
            res_db = supabase.table("questions_quiz").insert(dados_word).execute()
            st.session_state.pool_questoes = [q['id_quiz'] for q in res_db.data]
            supabase.table("game_state_quiz").update({
                "current_question_index_quiz": -1, 
                "is_active_quiz": False, 
                "show_answer_quiz": False,
                "buzzer_winner_quiz": None
            }).eq("id_quiz", 1).execute()
            st.sidebar.success(f"{len(dados_word)} questões carregadas!")
            st.rerun()

        st.sidebar.divider()
        
        res_players = supabase.table("players_quiz").select("*").execute()
        players_data = res_players.data
        if st.sidebar.button("📋 JOGADORES"):
            st.session_state.show_players_list = not st.session_state.show_players_list

        if st.session_state.show_players_list:
            for p in players_data:
                col_p1, col_p2 = st.sidebar.columns()
                col_p1.text(f"👤 {p['nickname_quiz']}")
                if col_p2.button("❌", key=f"del_{p['id_quiz']}"):
                    supabase.table("players_quiz").delete().eq("id_quiz", p['id_quiz']).execute()
                    st.rerun()

        st.sidebar.markdown(f'<div class="contador-jogadores">JOGADORES ON-LINE: {len(players_data)}</div>', unsafe_allow_html=True)
        st.sidebar.divider()

        t_padrao = st.sidebar.number_input("Tempo", value=15)
        
        if st.sidebar.button("🎲 PRÓXIMA PERGUNTA ALEATÓRIA", use_container_width=True):
            if st.session_state.pool_questoes:
                id_sorteado = random.choice(st.session_state.pool_questoes)
                st.session_state.pool_questoes.remove(id_sorteado)
                supabase.table("game_state_quiz").update({
                    "current_question_index_quiz": id_sorteado,
                    "is_active_quiz": True,
                    "show_answer_quiz": False,
                    "timer_duration_quiz": t_padrao,
                    "start_time_quiz": int(time.time()),
                    "buzzer_winner_quiz": None
                }).eq("id_quiz", 1).execute()
            else:
                supabase.table("game_state_quiz").update({"current_question_index_quiz": -2}).eq("id_quiz", 1).execute()
            st.rerun()

        if st.sidebar.button("🔄 RESET CRONÔMETRO", use_container_width=True):
            supabase.table("game_state_quiz").update({"is_active_quiz": False, "show_answer_quiz": False, "buzzer_winner_quiz": None}).eq("id_quiz", 1).execute()
            st.rerun()

        if st.sidebar.button("✅ VER RESPOSTA", use_container_width=True):
            supabase.table("game_state_quiz").update({"show_answer_quiz": True, "is_active_quiz": False}).eq("id_quiz", 1).execute()
            st.rerun()

        if st.sidebar.button("♻️ REINICIAR QUIZ", use_container_width=True):
            res_all = supabase.table("questions_quiz").select("id_quiz").execute()
            st.session_state.pool_questoes = [q['id_quiz'] for q in res_all.data]
            supabase.table("game_state_quiz").update({
                "current_question_index_quiz": -1, 
                "is_active_quiz": False, 
                "show_answer_quiz": False,
                "buzzer_winner_quiz": None
            }).eq("id_quiz", 1).execute()
            st.rerun()

    # --- 7. TELA DO JOGO ---
    st.markdown('<h1 style="text-align:center; color:#333;">TESTE SEUS CONHECIMENTOS</h1>', unsafe_allow_html=True)
    g_res = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    
    if g_res['current_question_index_quiz'] == -2:
        st.balloons()
        st.success("🎉 TODAS AS PERGUNTAS FORAM RESPONDIDAS!")
    elif g_res['current_question_index_quiz'] != -1:
        res_q_db = supabase.table("questions_quiz").select("*").eq("id_quiz", g_res['current_question_index_quiz']).execute()
        
        if res_q_db.data:
            q_data = res_q_db.data[0]
            st.markdown(f'<div class="caixa-pergunta">{q_data["question_text_quiz"]}</div>', unsafe_allow_html=True)
            
            # --- LÓGICA DO BUZZER (QUEM CLICA PRIMEIRO) ---
            if g_res['is_active_quiz']:
                # Nome do usuário atual para registrar no clique
                user_nick = st.session_state.auth.get('nickname', 'Anônimo')
                
                timer_html = f"""
                <div id="t-ui" class="display-cronometro">--</div>
                <div id="m-ui" style="text-align:center;"></div>
                <script>
                    var dur = {g_res['timer_duration_quiz']}; var ini = {g_res['start_time_quiz']};
                    var d_el = document.getElementById('t-ui'); var m_el = document.getElementById('m-ui');
                    function registrarClique() {{
                        window.parent.postMessage({{type: 'streamlit:setComponentValue', value: '{user_nick}'}}, '*');
                    }}
                    var tick = setInterval(function() {{
                        var agora = Math.floor(Date.now() / 1000); var resto = dur - (agora - ini);
                        if (resto > 0) {{ d_el.innerHTML = resto; }}
                        else {{
                            d_el.innerHTML = "0"; d_el.style.background = "#C00000";
                            m_el.innerHTML = '<button onclick="registrarClique()" style="background-color:#C00000; color:white; padding:25px; text-align:center; font-size:30px; font-weight:bold; border:6px solid #000; border-radius:20px; cursor:pointer; width:100%; margin-top:20px;">✋ APERTE PARA RESPONDER!</button>';
                            clearInterval(tick);
                        }}
                    }}, 1000);
                </script>
                """
                # Captura o clique do JS
                clique_detectado = components.html(timer_html, height=280)
                
                # Se alguém clicou e ainda não há vencedor registrado no banco nesta rodada
                if clique_detectado and not g_res.get('buzzer_winner_quiz'):
                    supabase.table("game_state_quiz").update({"buzzer_winner_quiz": clique_detectado}).eq("id_quiz", 1).execute()
                    st.rerun()

            # Exibe o vencedor se alguém já tiver apertado
            if g_res.get('buzzer_winner_quiz'):
                st.markdown(f'<div class="vencedor-buzzer">🔔 VEZ DE RESPONDER: {g_res["buzzer_winner_quiz"]}</div>', unsafe_allow_html=True)
            
            if g_res['show_answer_quiz']:
                st.markdown(f"""
                    <div style="background-color: #D4EDDA; padding: 25px; border-radius: 10px; border: 2px solid #28A745; font-size: 28px; font-weight: bold; text-align: center; color: #155724;">
                        RESPOSTA: {q_data['answer_text_quiz']}
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Aguardando o Administrador iniciar o Quiz.")
