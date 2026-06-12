import streamlit as st
import mido
import numpy as np
import random
import io
import pandas as pd

# ==========================================
# FUNÇÃO AUXILIAR: CONVERTE NÚMERO MIDI PARA NOTA
# ==========================================
def midi_para_nome_nota(numero_midi):
    """
    Converte um número MIDI (ex: 60) para o nome da nota por extenso (ex: DÓ 4).
    """
    nomes = ["DÓ", "DÓ#", "RÉ", "RÉ#", "MI", "FÁ", "FÁ#", "SOL", "SOL#", "LÁ", "LÁ#", "SI"]
    
    # O resto da divisão por 12 dá a nota dentro da oitava
    indice_nota = numero_midi % 12
    # A divisão inteira menos 1 dá a oitava musical correspondente
    oitava = (numero_midi // 12) - 1
    
    return f"{nomes[indice_nota]} {oitava}"

# ==========================================
# PASSO 1: EXTRAÇÃO DE DADOS MIDI (Adaptado para Upload Web)
# ==========================================
def extrair_dados_midi_stream(arquivo_bytes):
    arquivo_midi = mido.MidiFile(file=io.BytesIO(arquivo_bytes))
    sequencia_notas = []
    sequencia_ritmos = []
    
    for faixa in arquivo_midi.tracks:
        tempo_acumulado = 0
        nota_ativa = None
        
        for msg in faixa:
            tempo_acumulado += msg.time
            
            if msg.type == 'note_on' and msg.velocity > 0:
                if nota_ativa is not None and tempo_acumulado > 0:
                    sequencia_notas.append(nota_ativa)
                    sequencia_ritmos.append(tempo_acumulado)
                    tempo_acumulado = 0
                nota_ativa = msg.note
                
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if nota_ativa is not None and msg.note == nota_ativa:
                    sequencia_notas.append(nota_ativa)
                    sequencia_ritmos.append(tempo_acumulado)
                    tempo_acumulado = 0
                    nota_ativa = None
                    
    return sequencia_notas, sequencia_ritmos

# ==========================================
# PASSO 2: CÁLCULO DE PROBABILIDADES
# ==========================================
def analisar_estados_compostos_complexos(notas, ritmos_brutos):
    ritmos_limpos = [int(round(r / 10.0)) * 10 for r in ritmos_brutos]
    sequencia_estados = [(notas[i], ritmos_limpos[i]) for i in range(len(notas))]
    estados_unicos = sorted(list(set(sequencia_estados)))
    num_estados = len(estados_unicos)
    
    estado_para_idx = {estado: i for i, estado in enumerate(estados_unicos)}
    
    matriz_contagem = np.zeros((num_estados, num_estados))
    for i in range(len(sequencia_estados) - 1):
        atual = sequencia_estados[i]
        proximo = sequencia_estados[i+1]
        
        linha = estado_para_idx[atual]
        coluna = estado_para_idx[proximo]
        matriz_contagem[linha][coluna] += 1
        
    matriz_probabilidade = np.zeros((num_estados, num_estados))
    for i in range(num_estados):
        soma_linha = np.sum(matriz_contagem[i])
        if soma_linha > 0:
            matriz_probabilidade[i] = matriz_contagem[i] / soma_linha
            
    return matriz_probabilidade, estados_unicos

# ==========================================
# PASSO 3: GERADOR ESTOCÁSTICO
# ==========================================
def gerar_nova_melodia(matriz_probabilidade, estados_unicos, estado_inicial, tamanho_melodia):
    estado_para_idx = {estado: i for i, estado in enumerate(estados_unicos)}
    
    if estado_inicial not in estado_para_idx:
        estado_atual = estados_unicos[0]
    else:
        estado_atual = estado_inicial
        
    melodia_gerada = [estado_atual]
    
    for _ in range(tamanho_melodia - 1):
        idx_current = estado_para_idx[estado_atual]
        probabilidades_linha = matriz_probabilidade[idx_current]
        
        if np.sum(probabilidades_linha) == 0:
            proximo_estado = random.choice(estados_unicos)
        else:
            proximo_estado = random.choices(estados_unicos, weights=probabilidades_linha, k=1)[0]
            
        melodia_gerada.append(proximo_estado)
        estado_atual = proximo_estado
        
    return melodia_gerada

# ==========================================
# PASSO 4: EXPORTAR PARA MEMÓRIA (DOWNLOAD WEB)
# ==========================================
def salvar_midi_complexo_stream(melodia_gerada):
    novo_midi = mido.MidiFile()
    nova_faixa = mido.MidiTrack()
    novo_midi.tracks.append(nova_faixa)
    
    for nota, duracao_ticks in melodia_gerada:
        tempo_nota = max(duracao_ticks, 20)
        nova_faixa.append(mido.Message('note_on', note=nota, velocity=64, time=0))
        nova_faixa.append(mido.Message('note_off', note=nota, velocity=0, time=tempo_nota))
        
    memoria_arquivo = io.BytesIO()
    novo_midi.save(file=memoria_arquivo)
    return memoria_arquivo.getvalue()

# ==========================================
# INTERFACE VISUAL DO STREAMLIT
# ==========================================
st.set_page_config(page_title="Gerador Markov", layout="wide")

st.title("Gerador de melodias com Cadeias de Markov")
st.markdown("Insira uma partitura MIDI (.mid) para visualizar a matriz estocástica com notas reais e o processo de sorteio probabilístico.")
st.write("---")

if "bytes_saida" not in st.session_state:
    st.session_state.bytes_saida = None
if "historico_geracao" not in st.session_state:
    st.session_state.historico_geracao = None

arquivo_enviado = st.file_uploader("Escolha um arquivo MIDI de entrada (.mid)", type=["mid"])

if arquivo_enviado is not None:
    bytes_midi = arquivo_enviado.read()
    
    # PASSO 1: Extração
    notas_originais, ritmos_originais = extrair_dados_midi_stream(bytes_midi)
    qtd_notas_original = len(notas_originais)
    
    # PASSO 2: Treina a matriz
    matriz_p, lista_estados = analisar_estados_compostos_complexos(notas_originais, ritmos_originais)
    qtd_estados_unicos = len(lista_estados)
    
    # --- SEÇÃO 1: DADOS DA MÚSICA ---
    st.write("###  Dados e Estrutura da Música")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total de Notas Originais", value=qtd_notas_original)
    with col2:
        st.metric(label="Estados Compostos Únicos (Tamanho da Matriz)", value=f"{qtd_estados_unicos}x{qtd_estados_unicos}")
        
    # --- SEÇÃO 2: VISUALIZAÇÃO DA MATRIZ TRADUZIDA ---
    st.write("###  Matriz de Probabilidade de Transição")
    st.markdown("Esta tabela mostra a probabilidade de o estado da linha saltar para o estado da coluna:")
    
    legendas_estados = [f"{midi_para_nome_nota(e[0])} | {e[1]} Ticks" for e in lista_estados]
    
    df_matriz = pd.DataFrame(matriz_p, index=legendas_estados, columns=legendas_estados)
    st.dataframe(df_matriz.style.format("{:.2f}"), use_container_width=True)
    
    st.write("---")
    st.write("###  Configurações e Geração")
    
    tamanho_desejado = st.slider(
        "Quantidade de notas a gerar na nova música:", 
        min_value=10, 
        max_value=1000, 
        value=qtd_notas_original
    )
    
    if st.button("Compor Nova Melodia", type="primary"):
        with st.spinner("Realizando caminhada estocástica de Markov..."):
            primeiro_ritmo = int(round(ritmos_originais[0] / 10.0)) * 10
            inicio = (notas_originais[0], primeiro_ritmo)
            
            # PASSO 3: Geração
            nova_musica = gerar_nova_melodia(matriz_p, lista_estados, inicio, tamanho_melodia=tamanho_desejado)
            st.session_state.historico_geracao = nova_musica
            
            # PASSO 4: Exportação
            st.session_state.bytes_saida = salvar_midi_complexo_stream(nova_musica)
            st.success("Nova melodia composta com sucesso!")

    # --- SEÇÃO 3: PROCESSO DE GERAÇÃO TRADUZIDO ---
    if st.session_state.historico_geracao is not None:
        st.write("###  Auditoria do Processo de Geração Melódica")
        
        with st.expander("Clique aqui para inspecionar a sequência de sorteios passo a passo"):
            st.markdown("O algoritmo realizou a seguinte caminhada aleatória (Markov Chain Walk) pelas probabilidades da matriz:")
            
            dados_passos = []
            for i, (nota, ritmo) in enumerate(st.session_state.historico_geracao):
                dados_passos.append({
                    "Ordem do Sorteio": f"Nota #{i+1:03d}",
                    "Nota Sorteada": midi_para_nome_nota(nota),
                    "Duração (Ticks)": ritmo
                })
            
            df_passos = pd.DataFrame(dados_passos)
            st.table(df_passos.head(50))
            if len(dados_passos) > 50:
                st.caption(f"... e mais {len(dados_passos) - 50} notas foram sorteadas seguindo a mesma lógica matemática.")

    # Se a música já foi gerada, mostra o botão de download
    if st.session_state.bytes_saida is not None:
        st.write("---")
        st.write("###  Baixar sua Composição")
        st.download_button(
            label="Download do Arquivo MIDI Gerado",
            data=st.session_state.bytes_saida,
            file_name="melodia_markov.mid",
            mime="audio/midi"
        )
else:
    st.session_state.bytes_saida = None
    st.session_state.historico_geracao = None
    st.warning("Por favor, envie um arquivo MIDI acima para ativar a análise estatística do algoritmo.")