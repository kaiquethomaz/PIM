import json
import os
import hashlib
import socket
import threading
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# ==================== ARQUIVOS JSON (SÓ O SERVIDOR ACESSA) ====================
ARQ_PROF = "professores.json"
ARQ_ALUN = "alunos.json"
ARQ_TURM = "turmas.json"
ARQ_ATIV = "atividades.json"

# ==================== DADOS EM MEMÓRIA (CARREGADOS NO SERVIDOR) ====================
professores = []
alunos = []
turmas = []
atividades = []

# Trava para evitar que dois clientes salvem ao mesmo tempo
dados_lock = threading.Lock()

# ==================== UTILITÁRIOS (SÓ NO SERVIDOR) ====================
def carregar_arquivo(nome, default=[]):
    with dados_lock: # Trava o arquivo para leitura
        if os.path.exists(nome):
            # Tenta ler o arquivo
            try:
                with open(nome, "r", encoding="utf-8") as f:
                    # Se o arquivo estiver vazio, retorna o padrão
                    conteudo = f.read()
                    if not conteudo:
                        return default
                    return json.loads(conteudo)
            except json.JSONDecodeError:
                print(f"AVISO: Arquivo '{nome}' corrompido ou vazio. Iniciando com dados padrão.")
                return default
            except Exception as e:
                print(f"ERRO ao ler {nome}: {e}")
                return default
        return default

def salvar_arquivo(nome, dados):
    with dados_lock: # Trava o arquivo para escrita
        try:
            with open(nome, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"ERRO CRÍTICO ao salvar {nome}: {e}")

def salvar_tudo():
    """Função crítica: Salva todas as mudanças em disco."""
    # !!! CORREÇÃO AQUI !!!
    # Removemos o 'with dados_lock:' desta função,
    # pois a função 'salvar_arquivo' já gerencia a trava.
    salvar_arquivo(ARQ_PROF, professores)
    salvar_arquivo(ARQ_ALUN, alunos)
    salvar_arquivo(ARQ_TURM, turmas)
    salvar_arquivo(ARQ_ATIV, atividades)

def carregar_tudo():
    """Carrega todos os JSONs para a memória do servidor."""
    global professores, alunos, turmas, atividades
    print(">> Carregando 'professores.json'...")
    professores = carregar_arquivo(ARQ_PROF, [])
    print(">> Carregando 'alunos.json'...")
    alunos = carregar_arquivo(ARQ_ALUN, [])
    print(">> Carregando 'turmas.json'...")
    turmas = carregar_arquivo(ARQ_TURM, [])
    print(">> Carregando 'atividades.json'...")
    atividades = carregar_arquivo(ARQ_ATIV, [])
    
    # Garante que os arquivos existam no primeiro boot (se estavam vazios)
    print(">> Verificando e salvando arquivos...")
    salvar_tudo() # Agora esta função vai funcionar sem travar

def prox_id(lista):
    # Garante que o ID seja sempre um inteiro
    ids = [int(x.get("id", 0)) for x in lista if str(x.get("id")).isdigit()]
    return max(ids, default=0) + 1


def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# ==================== BUSCAS (SÓ NO SERVIDOR) ====================
def buscar_professor_por_id(pid):
    try:
        pid_int = int(pid)
        return next((p for p in professores if p["id"] == pid_int), None)
    except ValueError:
        return None

def buscar_aluno_por_id(aid):
    try:
        aid_int = int(aid)
        return next((a for a in alunos if a["id"] == aid_int), None)
    except ValueError:
        return None

def buscar_turma_por_id(tid):
    try:
        tid_int = int(tid)
        return next((t for t in turmas if t["id"] == tid_int), None)
    except ValueError:
        return None

def buscar_atividade_por_id(aid):
    try:
        aid_int = int(aid)
        return next((a for a in atividades if a["id"] == aid_int), None)
    except ValueError:
        return None

# ==================== FUNÇÕES DE LÓGICA (MODIFICADAS PARA O SERVIDOR) ====================
# Todas as funções recebem parâmetros, fazem a lógica, salvam no JSON, e retornam uma string de status.

def login_professor(matricula, senha_plana):
    """Processa o login. Recebe credenciais, retorna o dicionário do professor ou None."""
    senha_hash = hash_senha(senha_plana)
    for p in professores:
        if p["matricula"] == matricula and p["senha"] == senha_hash:
            print(f"[Log Servidor] Login bem-sucedido para: {p['nome']}")
            return p
    print(f"[Log Servidor] Tentativa de login falhou para matrícula: {matricula}")
    return None

# --- Módulo Professores ---
def listar_professores():
    if not professores: return json.dumps([])
    return json.dumps(professores)

def cadastrar_professor(nome, matricula, senha_plana):
    if any(p["matricula"].lower() == matricula.lower() for p in professores):
        return "❌ ERRO: Matrícula já cadastrada."
    pid = prox_id(professores)
    professores.append({"id": pid, "nome": nome, "matricula": matricula, "senha": hash_senha(senha_plana)})
    salvar_arquivo(ARQ_PROF, professores)
    print(f"[Log Servidor] Professor cadastrado: {nome}")
    return "✅ Professor cadastrado."

def editar_professor(pid_str, novo_nome, nova_mat, nova_senha_plana):
    p = buscar_professor_por_id(pid_str)
    if not p: return "❌ ERRO: Professor não encontrado."
    if novo_nome: p["nome"] = novo_nome
    if nova_mat: p["matricula"] = nova_mat
    if nova_senha_plana: p["senha"] = hash_senha(nova_senha_plana)
    salvar_arquivo(ARQ_PROF, professores)
    print(f"[Log Servidor] Professor editado: ID {pid_str}")
    return "✅ Professor atualizado."

def remover_professor(pid_str):
    p = buscar_professor_por_id(pid_str)
    if not p: return "❌ ERRO: Professor não encontrado."
    professores.remove(p)
    salvar_arquivo(ARQ_PROF, professores)
    print(f"[Log Servidor] Professor removido: {p['nome']}")
    return "✅ Professor removido."

# --- Módulo Alunos ---
def listar_alunos():
    if not alunos: return json.dumps([])
    return json.dumps(alunos)

def cadastrar_aluno(nome, matricula):
    if any(x["matricula"].lower() == matricula.lower() for x in alunos):
        return "❌ ERRO: Matrícula já cadastrada."
    aid = prox_id(alunos)
    alunos.append({"id": aid, "nome": nome, "matricula": matricula})
    salvar_arquivo(ARQ_ALUN, alunos)
    print(f"[Log Servidor] Aluno cadastrado: {nome}")
    return "✅ Aluno cadastrado."

def editar_aluno(aid_str, novo_nome, nova_mat):
    a = buscar_aluno_por_id(aid_str)
    if not a: return "❌ ERRO: Aluno não encontrado."
    if novo_nome: a['nome'] = novo_nome
    if nova_mat: a['matricula'] = nova_mat
    salvar_arquivo(ARQ_ALUN, alunos)
    print(f"[Log Servidor] Aluno editado: ID {aid_str}")
    return "✅ Aluno atualizado."

def remover_aluno(aid_str):
    a = buscar_aluno_por_id(aid_str)
    if not a: return "❌ ERRO: Aluno não encontrado."
    
    aid = a['id'] # Pega o ID numérico
    for t in turmas:
        if aid in t.get("alunos", []):
            t["alunos"].remove(aid)
    for atv in atividades:
        if str(aid) in atv.get("notas", {}):
            del atv["notas"][str(aid)]
    alunos.remove(a)
    
    salvar_tudo()
    print(f"[Log Servidor] Aluno removido: {a['nome']}")
    return "✅ Aluno removido."

def buscar_aluno(query):
    encontrados = [a for a in alunos if query in a["nome"].lower() or query in a["matricula"].lower()]
    return json.dumps(encontrados)

def ver_turmas_do_aluno(aid_str):
    a = buscar_aluno_por_id(aid_str)
    if not a: return "❌ ERRO: Aluno não encontrado."
    
    aid = a['id']
    turmas_do_aluno = [t for t in turmas if aid in t.get("alunos", [])]
    if not turmas_do_aluno:
        return "Aluno não está matriculado em nenhuma turma."
    turmas_info = [{"id": t["id"], "nome": t["nome"]} for t in turmas_do_aluno]
    return json.dumps(turmas_info)

# --- Módulo Turmas ---
def listar_turmas():
    if not turmas: return json.dumps([])
    lista = []
    for t in turmas:
        lista.append({
            "id": t.get('id', 0), 
            "nome": t.get('nome', 'N/D'), 
            "alunos": len(t.get('alunos', [])), 
            "atividades": len(t.get('atividades',[]))
        })
    return json.dumps(lista)

def cadastrar_turma(nome):
    tid = prox_id(turmas)
    turmas.append({"id": tid, "nome": nome, "alunos": [], "atividades": []})
    salvar_arquivo(ARQ_TURM, turmas)
    print(f"[Log Servidor] Turma cadastrada: {nome}")
    return "✅ Turma cadastrada."

def editar_turma(tid_str, novo_nome):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    if novo_nome: t['nome'] = novo_nome
    salvar_arquivo(ARQ_TURM, turmas)
    print(f"[Log Servidor] Turma editada: ID {tid_str}")
    return "✅ Turma atualizada."

def remover_turma(tid_str):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    
    tid = t['id']
    atv_to_remove = [a for a in atividades if a.get("turma_id") == tid]
    for a in atv_to_remove:
        atividades.remove(a)
    turmas.remove(t)
    salvar_tudo()
    print(f"[Log Servidor] Turma removida: {t['nome']}")
    return "✅ Turma e atividades associadas removidas."

def ver_alunos_da_turma(tid_str):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    if not t.get("alunos"): return "Nenhum aluno matriculado nesta turma."
    
    lista_alunos_turma = []
    for aid in t["alunos"]:
        a = buscar_aluno_por_id(aid)
        if a:
            lista_alunos_turma.append({"id": a['id'], "matricula": a['matricula'], "nome": a['nome']})
    return json.dumps(lista_alunos_turma)

def ver_atividades_da_turma(tid_str):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    if not t.get("atividades"): return "Nenhuma atividade nesta turma."

    lista_atv_turma = []
    for aid in t["atividades"]:
        atv = buscar_atividade_por_id(aid)
        if atv:
            lista_atv_turma.append({"id": atv['id'], "nome": atv['nome'], "descricao": atv.get("descricao", "")})
    return json.dumps(lista_atv_turma)

def matricular_aluno_em_turma(aid_str, tid_str):
    a = buscar_aluno_por_id(aid_str)
    t = buscar_turma_por_id(tid_str)
    if not a: return "❌ ERRO: Aluno não encontrado."
    if not t: return "❌ ERRO: Turma não encontrada."
    
    aid = a['id']
    if aid in t.get("alunos", []): return "Aluno já matriculado."
    
    t["alunos"].append(aid)
    salvar_arquivo(ARQ_TURM, turmas)
    print(f"[Log Servidor] Aluno {a['nome']} matriculado na {t['nome']}")
    return "✅ Matriculado com sucesso."

def desmatricular_aluno(tid_str, aid_str):
    t = buscar_turma_por_id(tid_str)
    a = buscar_aluno_por_id(aid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    if not a: return "❌ ERRO: Aluno não encontrado."
    
    aid = a['id']
    if aid not in t.get("alunos", []): return "❌ ERRO: Aluno não está matriculado nessa turma."
    
    t["alunos"].remove(aid)
    for atv_id in list(t.get("atividades", [])):
        atv = buscar_atividade_por_id(atv_id)
        if atv and str(aid) in atv.get("notas", {}):
            del atv["notas"][str(aid)]
    salvar_tudo()
    print(f"[Log Servidor] Aluno ID {aid} desmatriculado da {t['nome']}")
    return "✅ Desmatriculado."

# --- Módulo Atividades e Notas ---
def listar_atividades():
    if not atividades: return json.dumps([])
    lista = []
    for a in atividades:
        t = buscar_turma_por_id(a.get("turma_id"))
        lista.append({
            "id": a.get('id', 0),
            "nome": a.get('nome', 'N/D'),
            "turma_nome": t["nome"] if t else "N/D",
            "descricao": a.get("descricao", "")
        })
    return json.dumps(lista)

def cadastrar_atividade(tid_str, nome, descricao):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    
    aid = prox_id(atividades)
    atv = {"id": aid, "nome": nome, "descricao": descricao, "turma_id": t['id'], "notas": {}}
    atividades.append(atv)
    t.setdefault("atividades", []).append(aid)
    salvar_tudo()
    print(f"[Log Servidor] Atividade '{nome}' cadastrada na {t['nome']}")
    return "✅ Atividade cadastrada."

def editar_atividade(aid_str, novo_nome, nova_descr):
    atv = buscar_atividade_por_id(aid_str)
    if not atv: return "❌ ERRO: Atividade não encontrada."
    if novo_nome: atv["nome"] = novo_nome
    if nova_descr: atv["descricao"] = nova_descr
    salvar_arquivo(ARQ_ATIV, atividades)
    print(f"[Log Servidor] Atividade editada: ID {aid_str}")
    return "✅ Atividade atualizada."

def remover_atividade(aid_str):
    atv = buscar_atividade_por_id(aid_str)
    if not atv: return "❌ ERRO: Atividade não encontrada."
    
    tid = atv.get("turma_id")
    if tid:
        t = buscar_turma_por_id(tid)
        if t and atv['id'] in t.get("atividades", []):
            t["atividades"].remove(atv['id'])
    atividades.remove(atv)
    salvar_tudo()
    print(f"[Log Servidor] Atividade removida: {atv['nome']}")
    return "✅ Atividade removida."

def ver_notas_atividade(aid_str):
    atv = buscar_atividade_por_id(aid_str)
    if not atv: return "❌ ERRO: Atividade não encontrada."
    if not atv.get("notas"): return "Sem notas registradas."
    
    lista_notas = []
    for sid, nota in atv["notas"].items():
        aluno = buscar_aluno_por_id(sid)
        lista_notas.append({
            "id_aluno": sid,
            "nome": aluno["nome"] if aluno else "Aluno Removido",
            "nota": nota
        })
    return json.dumps(lista_notas)

def adicionar_editar_nota(atv_id_str, aluno_id_str, nota_str):
    atv = buscar_atividade_por_id(atv_id_str)
    aluno = buscar_aluno_por_id(aluno_id_str)
    if not atv: return "❌ ERRO: Atividade não encontrada."
    if not aluno: return "❌ ERRO: Aluno não encontrado."

    try:
        nota = float(nota_str.replace(",", "."))
        if not (0.0 <= nota <= 10.0): return "❌ ERRO: Nota deve ser entre 0 e 10."
    except ValueError:
        return "❌ ERRO: Nota deve ser um número."
        
    t = buscar_turma_por_id(atv.get("turma_id"))
    if not t: return "❌ ERRO: Turma da atividade não encontrada."
    if aluno['id'] not in t.get("alunos", []): return "❌ ERRO: Aluno não pertence a esta turma."
    
    atv.setdefault("notas", {})[str(aluno['id'])] = nota
    salvar_arquivo(ARQ_ATIV, atividades)
    print(f"[Log Servidor] Nota {nota} registrada para Aluno ID {aluno_id_str} em Atividade ID {atv_id_str}")
    return "✅ Nota registrada/atualizada."

def remover_nota(atv_id_str, aluno_id_str):
    atv = buscar_atividade_por_id(atv_id_str)
    if not atv: return "❌ ERRO: Atividade não encontrada."
    if aluno_id_str in atv.get("notas", {}):
        del atv["notas"][aluno_id_str]
        salvar_arquivo(ARQ_ATIV, atividades)
        print(f"[Log Servidor] Nota removida para Aluno ID {aluno_id_str} em Atividade ID {atv_id_str}")
        return "✅ Nota removida."
    else:
        return "❌ ERRO: Nenhuma nota encontrada para esse aluno nesta atividade."
    
# --- Módulo Relatórios ---
def gerar_relatorio_texto(tid_str):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    
    resposta = [f"Relatório da Turma {t['nome']}"]
    if not t.get("alunos"):
        resposta.append("Sem alunos matriculados.")
        return "\n".join(resposta)
    
    for aid in t["alunos"]:
        a = buscar_aluno_por_id(aid)
        if not a: continue
        notas = []
        for atv_id in t.get("atividades", []):
            atv = buscar_atividade_por_id(atv_id)
            if atv and str(aid) in atv.get("notas", {}):
                notas.append(f"{atv['nome']}: {atv['notas'][str(aid)]}")
        resposta.append(f"{a['matricula']} - {a['nome']} -> {' | '.join(notas) if notas else 'Sem notas'}")
    
    print(f"[Log Servidor] Relatório Texto gerado para: {t['nome']}")
    return "\n".join(resposta)

def gerar_relatorios_pdf_turma(tid_str, nome_professor):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."

    filename = f"relatorio_turma_{t['id']}.pdf"
    try:
        c = canvas.Canvas(filename, pagesize=letter)
        c.setFont("Helvetica-Bold", 14)
        width, height = letter
        y = height - 50
        c.drawString(50, y, f"Relatório - Turma {t['nome']}")
        c.setFont("Helvetica", 10)
        c.drawString(50, y-15, f"Gerado por: Prof. {nome_professor}")
        y -= 50
        c.setFont("Helvetica", 12)
        if not t.get("alunos"):
            c.drawString(50, y, "Sem alunos matriculados.")
        else:
            for aid in t["alunos"]:
                a = buscar_aluno_por_id(aid)
                if not a: continue
                c.drawString(50, y, f"{a['matricula']} - {a['nome']}")
                y -= 20
                for atv_id in t.get("atividades", []):
                    atv = buscar_atividade_por_id(atv_id)
                    if atv and str(aid) in atv.get("notas", {}):
                        c.drawString(70, y, f"{atv['nome']}: {atv['notas'][str(aid)]}")
                        y -= 18
                y -= 8
                if y < 70:
                    c.showPage()
                    c.setFont("Helvetica", 12)
                    y = height - 40
        c.save()
        print(f"[Log Servidor] PDF de Turma gerado: {filename}")
        return f"✅ SUCESSO: PDF '{filename}' gerado na máquina do servidor."
    except Exception as e:
        return f"❌ ERRO ao gerar PDF: {e}"

def gerar_boletins_pdf(nome_professor, corte_aprovacao_str="6.0"):
    print(f"[Log Servidor] Gerando boletins (PDF) por Prof. {nome_professor}")
    if not alunos: return "❌ ERRO: Não há alunos cadastrados."
    
    try:
        corte_aprovacao = float(corte_aprovacao_str.replace(",","."))
        pasta = "boletins_alunos"
        os.makedirs(pasta, exist_ok=True)
        count = 0

        for aluno in alunos:
            filename = os.path.join(pasta, f"boletim_{aluno['matricula']}_{aluno['id']}.pdf")
            c = canvas.Canvas(filename, pagesize=letter)
            width, height = letter
            margem_x = 2*cm
            y = height - 2*cm

            # (A lógica completa de desenho do PDF está aqui)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(margem_x, y, "Boletim Escolar")
            c.setFont("Helvetica", 10)
            c.drawString(width - margem_x - 200, y, f"Aluno: {aluno['nome']}")
            y -= 18
            c.drawString(margem_x, y, f"Matrícula: {aluno['matricula']}  |  ID: {aluno['id']}")
            y -= 24
            c.line(margem_x, y, width - margem_x, y)
            y -= 14

            medias_turmas = []
            turmas_do_aluno = [t for t in turmas if aluno['id'] in t.get('alunos', [])]
            
            if not turmas_do_aluno:
                c.drawString(margem_x, y, "Aluno não está matriculado em nenhuma turma.")
            else:
                for t in turmas_do_aluno:
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(margem_x, y, f"Turma: {t['nome']}")
                    y -= 16
                    c.setFont("Helvetica", 10)
                    c.drawString(margem_x, y, "Atividade")
                    c.drawString(margem_x + 8*cm, y, "Descrição")
                    c.drawString(margem_x + 14*cm, y, "Nota")
                    y -= 12
                    c.line(margem_x, y, width - margem_x, y)
                    y -= 8

                    notas_turma = []
                    ativs = [buscar_atividade_por_id(aid) for aid in t.get("atividades", []) if buscar_atividade_por_id(aid)]
                    
                    if not ativs:
                        c.drawString(margem_x, y, "Nenhuma atividade cadastrada nesta turma.")
                        y -= 18
                    else:
                        for atv in ativs:
                            nota = atv.get("notas", {}).get(str(aluno['id']), "—")
                            if nota != "—":
                                try: notas_turma.append(float(nota))
                                except: pass
                            c.drawString(margem_x, y, atv['nome'][:30])
                            c.drawString(margem_x + 8*cm, y, (atv.get('descricao', '')[:55]))
                            c.drawString(margem_x + 14*cm, y, str(nota))
                            y -= 14
                    
                    media_t = sum(notas_turma)/len(notas_turma) if notas_turma else None
                    if media_t is not None:
                        medias_turmas.append(media_t)
                        c.setFont("Helvetica-Bold", 10)
                        c.drawString(margem_x, y, f"Média da turma {t['nome']}: {media_t:.2f}")
                        y -= 16
                    y -= 6
            
            if medias_turmas:
                media_geral = sum(medias_turmas)/len(medias_turmas)
                situacao = "APROVADO" if media_geral >= corte_aprovacao else "REPROVADO"
                c.setFont("Helvetica-Bold", 12)
                c.drawString(margem_x, y, f"Média geral: {media_geral:.2f}   |   Situação: {situacao}")
            
            c.save()
            count += 1
            
        return f"✅ SUCESSO: {count} boletins gerados na pasta '{pasta}' no servidor."
    except Exception as e:
        return f"❌ ERRO ao gerar boletins PDF: {e}"

def gerar_relatorio_inteligente():
    print("[Log Servidor] Gerando Relatório Inteligente.")
    resposta = ["=== Relatório Inteligente ==="]
    if not turmas:
        resposta.append("\nNenhuma turma cadastrada para análise.")
        return "\n".join(resposta)

    for t in turmas:
        notas_turma = []
        for atv_id in t.get("atividades", []):
            atv = buscar_atividade_por_id(atv_id)
            if atv:
                notas_turma.extend(atv.get("notas", {}).values())
        
        media = sum(notas_turma)/len(notas_turma) if notas_turma else 0
        
        if media >= 8.5: analise = "Excelente desempenho"
        elif media >= 7: analise = "Bom desempenho"
        elif media >= 5: analise = "Desempenho mediano"
        else: analise = "Desempenho abaixo do esperado"
        resposta.append(f"\nTurma {t['nome']} - Média: {media:.2f} -> {analise}")
    return "\n".join(resposta)

def melhor_pior_aluno_turma(tid_str):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    
    resultados = []
    for aid in t.get("alunos", []):
        soma, cnt = 0, 0
        for atv_id in t.get("atividades", []):
            atv = buscar_atividade_por_id(atv_id)
            if atv and str(aid) in atv.get("notas", {}):
                soma += atv["notas"][str(aid)]
                cnt += 1
        media = soma/cnt if cnt>0 else None
        resultados.append({"aluno_id": aid, "media": media})
        
    com_notas = [r for r in resultados if r["media"] is not None]
    if not com_notas: return "Nenhum aluno com notas nesta turma."
    
    melhor = max(com_notas, key=lambda x: x["media"])
    pior = min(com_notas, key=lambda x: x["media"])
    a_melhor = buscar_aluno_por_id(melhor["aluno_id"])
    a_pior = buscar_aluno_por_id(pior["aluno_id"])
    
    resposta = [
        f"Melhor: {a_melhor['nome']} - Média: {melhor['media']:.2f}",
        f"Pior: {a_pior['nome']} - Média: {pior['media']:.2f}"
    ]
    return "\n".join(resposta)
    
# ==================== FUNÇÃO DE TRATAMENTO DE CONEXÃO ====================
def handle_client(conn, addr):
    """Trata toda a comunicação de um único cliente."""
    print(f"Cliente conectado: {addr}")
    usuario_logado_nesta_conexao = None
    try:
        while True:
            # Protocolo de recebimento: [TAMANHO: 10 bytes][MENSAGEM]
            tamanho_bytes = conn.recv(10)
            if not tamanho_bytes:
                break
            
            tamanho_msg = int(tamanho_bytes.decode('utf-8').strip())
            
            dados = b""
            while len(dados) < tamanho_msg:
                parte = conn.recv(min(tamanho_msg - len(dados), 4096))
                if not parte:
                    raise ConnectionError("Conexão perdida ao receber dados.")
                dados += parte
            
            comando = dados.decode('utf-8')
            print(f"[Comando de {addr}] {comando}")
            
            partes = comando.split(';')
            acao = partes[0]
            resposta = "❌ ERRO: Comando inválido ou não reconhecido."
            prof_logado = usuario_logado_nesta_conexao

            # --- Lógica de Acesso (Não precisa de login) ---
            if acao == "cadastrar_professor" and len(partes) == 4:
                resposta = cadastrar_professor(partes[1], partes[2], partes[3])
            
            elif acao == "login_professor" and len(partes) == 3:
                professor = login_professor(partes[1], partes[2])
                if professor:
                    usuario_logado_nesta_conexao = professor
                    resposta = f"SUCESSO_LOGIN:{professor['nome']}"
                else:
                    resposta = "❌ ERRO: Matrícula ou senha inválida."
            
            # --- Lógica Principal (Precisa de login) ---
            elif prof_logado:
                # --- Menu Professores ---
                if acao == "listar_professores":
                    resposta = listar_professores()
                elif acao == "editar_professor" and len(partes) == 5:
                    resposta = editar_professor(partes[1], partes[2], partes[3], partes[4])
                elif acao == "remover_professor" and len(partes) == 2:
                    resposta = remover_professor(partes[1])
                    
                # --- Menu Alunos ---
                elif acao == "listar_alunos":
                    resposta = listar_alunos()
                elif acao == "cadastrar_aluno" and len(partes) == 3:
                    resposta = cadastrar_aluno(partes[1], partes[2])
                elif acao == "editar_aluno" and len(partes) == 4:
                    resposta = editar_aluno(partes[1], partes[2], partes[3])
                elif acao == "remover_aluno" and len(partes) == 2:
                    resposta = remover_aluno(partes[1])
                elif acao == "buscar_aluno" and len(partes) == 2:
                    resposta = buscar_aluno(partes[1])
                elif acao == "ver_turmas_do_aluno" and len(partes) == 2:
                    resposta = ver_turmas_do_aluno(partes[1])

                # --- Menu Turmas ---
                elif acao == "listar_turmas":
                    resposta = listar_turmas()
                elif acao == "cadastrar_turma" and len(partes) == 2:
                    resposta = cadastrar_turma(partes[1])
                elif acao == "editar_turma" and len(partes) == 3:
                    resposta = editar_turma(partes[1], partes[2])
                elif acao == "remover_turma" and len(partes) == 2:
                    resposta = remover_turma(partes[1])
                elif acao == "ver_alunos_da_turma" and len(partes) == 2:
                    resposta = ver_alunos_da_turma(partes[1])
                elif acao == "ver_atividades_da_turma" and len(partes) == 2:
                    resposta = ver_atividades_da_turma(partes[1])
                elif acao == "matricular_aluno_em_turma" and len(partes) == 3:
                    resposta = matricular_aluno_em_turma(partes[1], partes[2])
                elif acao == "desmatricular_aluno" and len(partes) == 3:
                    resposta = desmatricular_aluno(partes[1], partes[2])
                
                # --- Menu Atividades ---
                elif acao == "listar_atividades":
                    resposta = listar_atividades()
                elif acao == "cadastrar_atividade" and len(partes) == 4:
                    resposta = cadastrar_atividade(partes[1], partes[2], partes[3])
                elif acao == "editar_atividade" and len(partes) == 4:
                    resposta = editar_atividade(partes[1], partes[2], partes[3])
                elif acao == "remover_atividade" and len(partes) == 2:
                    resposta = remover_atividade(partes[1])
                elif acao == "ver_notas_atividade" and len(partes) == 2:
                    resposta = ver_notas_atividade(partes[1])
                elif acao == "adicionar_editar_nota" and len(partes) == 4:
                    resposta = adicionar_editar_nota(partes[1], partes[2], partes[3])
                elif acao == "remover_nota" and len(partes) == 3:
                    resposta = remover_nota(partes[1], partes[2])
                
                # --- Menu Relatórios ---
                elif acao == "gerar_relatorio_texto" and len(partes) == 2:
                    resposta = gerar_relatorio_texto(partes[1])
                elif acao == "gerar_relatorios_pdf_turma" and len(partes) == 2:
                    resposta = gerar_relatorios_pdf_turma(partes[1], prof_logado['nome'])
                elif acao == "gerar_boletins_pdf":
                    resposta = gerar_boletins_pdf(prof_logado['nome'])
                elif acao == "gerar_relatorio_inteligente":
                    resposta = gerar_relatorio_inteligente()
                elif acao == "melhor_pior_aluno_turma" and len(partes) == 2:
                    resposta = melhor_pior_aluno_turma(partes[1])
                
                # --- Logout ---
                elif acao == "logout":
                    resposta = f"✅ SUCESSO_LOGOUT:Até logo, Prof. {prof_logado['nome']}."
                    print(f"[Log Servidor] Logout: {prof_logado['nome']}")
                    usuario_logado_nesta_conexao = None
            
            # --- Ação protegida sem login ---
            elif not prof_logado and acao not in ["cadastrar_professor", "login_professor"]:
                resposta = "❌ ERRO: Você precisa estar logado para executar esta ação."

            # --- Envio da Resposta ---
            resposta_bytes = resposta.encode('utf-8')
            tamanho = f"{len(resposta_bytes):<10}" # Protocolo de tamanho
            conn.sendall(tamanho.encode('utf-8') + resposta_bytes)
    
    except ConnectionResetError:
        print(f"Cliente {addr} desconectou abruptamente.")
    except Exception as e:
        print(f"Ocorreu um erro na conexão {addr}: {e}")
    
    print(f"Cliente {addr} desconectado.")
    conn.close()

# ==================== INICIAR SERVIDOR ====================
def iniciar_servidor():
    print(">> Carregando arquivos JSON...")
    carregar_tudo()
    print(">> Dados carregados. Iniciando servidor de rede...")
    
    HOST = '0.0.0.0'
    PORTA = 50007
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORTA))
        s.listen()
        print(f">> Servidor iniciado. Aguardando conexão na porta {PORTA}...")
        
        while True:
            conn, addr = s.accept()
            # Inicia uma nova thread para cada cliente
            # Isso permite que vários clientes se conectem ao mesmo tempo
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()

if __name__ == "__main__":
    iniciar_servidor()