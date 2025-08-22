import streamlit as st
import pandas as pd
import datetime
import re
import gspread
from google.oauth2.service_account import Credentials
import os
import json  # para tratar credenciais em JSON

# --- Configuração Inicial ---
st.set_page_config(page_title="Revisão do Regimento Interno", layout="wide")

# --- Constantes e Configuração do Google Sheets ---
# Nome EXATO da sua planilha Google
GOOGLE_SHEET_NAME = "NomeDaSuaPlanilhaDeFeedback"  # <<< MUDE AQUI
# Nome EXATO da aba/worksheet dentro da planilha
WORKSHEET_NAME = "Feedback"

# --- Dados do Regimento Interno (CHAVES MODIFICADAS PARA INCLUIR DICAS) ---
# Cole aqui o dicionário 'regimento_com_hints' completo, conforme sua base.
regimento_com_hints = {
    # Sumário (Apenas para referência, não revisável diretamente aqui)
    # "PREÂMBULO": """...""",
    "Item 1: Validade e Abrangência": "Este instrumento terá seu âmbito de validade e ação exclusivamente dentro dos domínios do RESIDENCIAL PARAÍSO DAS ÁGUAS, inclusive as áreas de proteção ambiental permanente.",
    "Item 2: Pessoas Sujeitas às Normas": "Estarão sujeitos às normas deste regulamento todas as pessoas, quer sejam proprietários, residentes, trabalhadores, prestadores de serviços, convidados, visitantes, entregadores ou que, por qualquer outra razão, estejam dentro do RESIDENCIAL PARAÍSO DAS ÁGUAS, ou em sua portaria de acesso, assim como seus veículos, meios de locomoção e equipamentos que estiverem portando ou conduzindo.",

    "CAPÍTULO I: DOS DIREITOS DOS ASSOCIADOS": "Define os direitos gerais de todos os associados do Residencial.",
    "Capítulo I - 1.1: Uso da unidade autônoma": "Usar, gozar e dispor da respective unidade autônoma, de acordo com o seu destino, nas condições a seguir previstas e em resoluções posteriores, desde que aprovadas em assembléia geral;",
    "Capítulo I - 1.2: Uso das áreas comuns": "Usar e gozar das partes de uso comum do RESIDENCIAL PARAÍSO DAS ÁGUAS, das áreas de lazer comunitárias e áreas de circulação interna, nos horários regulamentares e desde que não impeça idêntico uso e gozo dos demais moradores;",
    "Capítulo I - 1.3: Denúncia de irregularidades": "Denunciar à administração, exclusivamente por escrito, em livro próprio, que estará sempre disponível na Portaria, na sede da administração do Residencial, todas e quaisquer irregularidades que observe ou de que esteja sendo vítima:",
    "Capítulo I - 1.4: Participação em assembleias": "Comparecer às assembléias gerais, discutir, votar e ser votado obedecidoàs regras do estatuto social.",

    "CAPÍTULO II: DOS DEVERES E OBRIGAÇÕES": "Descreve os deveres e obrigações inalienáveis de cada associado morador.",
    "Capítulo II - 2.1: Cumprir o regulamento": "Cumprir e fazer cumprir rigorosamente este regulamento;",
    "Capítulo II - 2.2: Preservar moralidade e respeito": "Preservar e manter dentro do RESIDENCIAL PARAÍSO DAS ÁGUAS, a mais rigorosa moralidade, decência e respeito pessoal, às regras c pessoas de convívio interno:",
    "Capítulo II - 2.3: Acatar decisões": "Prestigiar, acatar e fazer acatar as decisões da assembleia e da administração do RESIDENCIAL PARAÍSO DAS ÁGUAS;",
    "Capítulo II - 2.4: Cooperar para harmonia": "Cooperar de forma efetiva, para a harmonia e perfeita convivência comunitária:",
    "Capítulo II - 2.5: Tratar funcionários com respeito": "Tratar com respeito e dignidade os empregados responsáveis pelas portarias, segurança, coleta de lixo, distribuição de correspondência interna, ou outros, e exigir dos mesmos idênticos tratamentos;",
    "Capítulo II - 2.6: Informar moradores da unidade": "Manter a administração do RESIDENCIAL PARAÍSO DAS ÁGUAS sempre informada dos moradores permanentes de cada unidade autônoma;",
    "Capítulo II - 2.7: Incluir regulamento em contratos": "Fazer constar como parte integrante dos eventuais contratos de locação, sublocação, cessão ou alienação, cópia deste regulamento e do estatuto;",
    "Capítulo II - 2.8: Comunicar ausência prolongada": "Comunicar à administração, ausência prolongada dos moradores da unidade autônoma, de forma a permitir a segurança maior atenção àquela unidade, inclusive impedindo o acesso de terceiros a casa;",
    "Capítulo II - 2.9: Pagar taxa de manutenção": "Pagar na data estabelecida a taxa de manutenção determinada pelaassembléia;",
    "Capítulo II - 2.10: Cumprir regras de segurança": "Cumprir e fazer cumprir rigorosamente as regras do sistema de segurança, constadas neste regulamento, uma vez que a inobservância ou negligência com as determinações ali adotadas colocará em risco todo o sistema de vigilância e segurança do RESIDENCIAL PARAÍSO DAS ÁGUAS;",
    "Capítulo II - 2.11: Acondicionar lixo corretamente": "Acondicionar o lixo doméstico em sacos e/ou recipientes apropriados, de acordo com sua seletividade, colocando-os nos locais e horário determinado;",
    "Capítulo II - 2.12: Respeitar horário de silêncio": "Guardar silêncio no período entre 24h00min e 07h00min da manhã seguinte, evitando alaridos e ruídos que prejudiquem ou incomodem a tranquilidade e o bem estar dos demais moradores, salvo se previamente autorizados por escrito pela Associação, emcasos de festas e comemorações, sendo proibida, ainda, a utilização de som automotivo em volume elevado;",
    "Capítulo II - 2.13: Manter lotes limpos e roçados": "Manter os lotes sempre limpos, com vegetação rente ao solo (roçados) e sem entulhos. O associado será notificado pela associação para promover a roçagem e limpeza do lote em até 15 (quinze) dias, não o fazendo a associação realizará a roçagem e limpeza do lote e lançará a despesa no boleto, bem como será aplicada multa conforme prevê o capítulo das penalidades.",

    "CAPÍTULO III: DAS PROIBIÇÕES": "Lista as atividades e ações que são proibidas dentro do Residencial Paraíso das Águas.",
    "Capítulo III - 3.1: Uso comercial/industrial/religioso da unidade": "Alugar, ceder ou explorar, no todo ou em parte a unidade autônoma para fins religiosos, comerciais ou industriais:",
    "Capítulo III - 3.1.1: Edificações não residenciais": "Edificar quaisquer obras, benfeitorias ou construções que não seja estritamente para fins da moradia familiar;",
    "Capítulo III - 3.2: Atos contra decoro e bom nome": "Praticar atos de violência ou atitudes que deponham contra o decoro, os costumes ou o bom nome do RESIDENCIAL PARAÍSO DAS ÁGUAS, responsabilizando-se igualmente pelos demais residentes ou convidados;",
    "Capítulo III - 3.3: Uso indevido de áreas comuns": "Utilizar ou permitir a utilização de objetos em área de uso comum para finalidades diversas das quais são destinados;",
    "Capítulo III - 3.4: Festas perturbadoras na unidade": "Alugar, ceder ou emprestar sua unidade para promover festividades ou reuniões que perturbarem a tranquilidade ou sossego dos demais moradores:",
    "Capítulo III - 3.5: Manifestações políticas/religiosas (áreas comuns)": "Manifestações políticas e religiosas nas áreas comuns:",
    "Capítulo III - 3.6: Usar funcionários para serviços particulares": "Utilizar os empregados do RESIDENCIAL PARAÍSO DAS ÁGUAS para serviços, particulares, durante seu horário de expediente normal de trabalho;",
    "Capítulo III - 3.7: Mudanças fora do horário": "Realizar mudanças fora do horário compreendido de 7:00 às 19:00 horas, diariamente:",
    "Capítulo III - 3.8: Movimentação de terra sem arrimo/aviso": "Fazer remoções ou colocações de aterro, taludes de acertos de movimentação de terra, de aterros ou cortes sem a construção de muros de arrimo na divisa, e comunicação prévia à administração, que poderá, a seu critério, solicitar um parecer técnico;",
    "Capítulo III - 3.9: Banho na represa fora de áreas definidas": "Banhar-se às margens da represa salvo nas áreas pré-definidas;",
    "Capítulo III - 3.10: Materiais/objetos perigosos na unidade": "Ter ou usar nas respectivas unidades autônomas, materiais, objetos, aparelhos einstalações suscetíveis de afetar de qualquer forma a saúde, segurança e tranquilidade dos demais moradores, segundo as normas legais em vigor;",
    "Capítulo III - 3.11: Jogar lixo nas áreas comuns": "Atirar, nos jardins, áreas comuns, vias de acesso, áreas de lazer, estacionamento e demais dependências, fragmentos de lixo, papéis, pontas de cigarro, ou quaisquer outros detritos ou objetos;",
    "Capítulo III - 3.12: Guardar substâncias perigosas": "Manter ou guardar substâncias perigosas à segurança do RESIDENCIAL PARAÍSO DAS ÁGUAS e de seus moradores, tais como: produtos químicos, radioativos, inflamáveis. e outros similares;",
    "Capítulo III - 3.13: Danificar jardins e áreas de preservação": "Danificar as partes que compõem os jardins, áreas de lazer e de preservação ambiental, bem como remover mudas ou plantas desses locais;",
    "Capítulo III - 3.14: Manter entulho visível na unidade": "Manter em sua unidade entulho ou restos de construção de forma que esteja denegrindo a beleza da fachada das casas;",
    "Capítulo III - 3.15: Fogueiras sem autorização": "E proibida a utilização da fogueira, devendo haver previa e expressa autorização da Administração;",
    "Capítulo III - 3.16: Reuniões/confraternizações (áreas comuns s/ autoriz.)": "Realizar reuniões ou confraternizações em áreas comuns, devendo haver expressa autorização da Administração;",
    "Capítulo III - 3.17: Uso de fogo para limpeza de lotes": "Utilizar o fogo para limpeza de lotes ou partes de lotes;",
    "Capítulo III - 3.18: Atracar flutuantes na orla": "Atracar ou possuir atracado qualquer tipo de flutuante na orla;",
    "Capítulo III - 3.19: Acampar na orla/áreas comuns": "Acampar na orla e nas áreas comuns do RESIDENCIAL PARAÍSO DAS ÁGUAS:",
    "Capítulo III - 3.20: Perfuração de poço artesiano": "É proibido fazer a perfuração de poço artesiano nos lotes.",
    "Capítulo III - 3.21: Disparos de armas de fogo/pressão": "É proibido fazer disparos de armas de fogo e/ou pressão nas áreas comuns e de proteção ambiental da Associação. Em caso de contrárias será aplicada a multa de até 10 (dez) taxas mensais.",

    "CAPÍTULO IV: DO SISTEMA DE SEGURANÇA INTERNA": "Aborda a estrutura e as regras gerais do sistema de segurança interna do Residencial.",
    "Capítulo IV - 4.1: Referência ao Anexo I": "Por tratar-se de item específico da maior relevância e sujeito a adequações circunstanciais e emergentes, constará de anexo próprio, parte integrante deste Regulamento;",
    "Capítulo IV - 4.2: Alterações futuras via assembleia": "As definições ou eventuais alterações relacionadas exclusivamente a segurança interna, posteriores a aprovação deste regulamento poderão ser adotadas com a aprovação de assembléia e amplamente divulgada internamente pelo Conselho.",

    "CAPÍTULO V: DOS PROCEDIMENTOS INTERNOS": "Detalha os procedimentos internos relacionados à portaria, uso de áreas comuns, criação de animais e preservação ambiental.",
    "Capítulo V - 5.1: PORTARIA - Acesso e Uso": "Define o acesso e uso das instalações da portaria.",
    "Capítulo V - 5.1.1: Prédio da portaria (patrimônio comum)": "O prédio da Portaria compõe-se de patrimônio comum do RESIDENCIAL PARAÍSO DAS AGUAS, onde localizar-se-á em caráter provisório a administração da Associação, e, portanto seu uso estará sujeito as regras conforme a seguir:",
    "Capítulo V - 5.1.2: Livre acesso de associados à portaria": "Todos os associados terão livre acesso às instalações da portaria, devendo inclusive zelar pelo seu bom funcionamento e manutenção dos critérios de seriedade e boa convivência que devem ser a tônica desse ambiente.",
    "Capítulo V - 5.2: FUNCIONAMENTO DA PORTARIA": "Estabelece as regras de funcionamento da portaria, identificação e acesso.",
    "Capítulo V - 5.2.1: Livre passagem de associados": "Todos os associados, devidamente identificados como tal, terão livre passagem pela portaria em qualquer horário, em todos os dias da semana;",
    "Capítulo V - 5.2.2: Identificação de residentes e veículos": "Caberá a cada associado identificar junto à segurança, todas as pessoas que vivem em sua residência (filhos, parentes, agregados, etc.), bem como os veículos utilizados:",
    "Capítulo V - 5.2.3: Comunicação de empregados": "Caberá ainda ao associado comunicar a administração à relação dos seus empregados permanentes e temporários e se terá alguma restrição quantas as suas entradas e saídas do RESIDENCIAL PARAÍSO DAS ÁGUAS;",
    "Capítulo V - 5.2.4: Formas de identificação": "As formas dessas identificações serão fornecidas pela segurança e alteradas sempre que solicitadas pelos associados;",
    "Capítulo V - 5.2.5: Identificação de visitantes/convidados": "Os visitantes e convidados que se dirigirem às moradias individuais deverão se identificar na portaria, obedecendo às regras determinadas pela segurança;",
    "Capítulo V - 5.2.6: Proibição de entrada (veículos pesados s/ autoriz.)": "Não será permitido o ingresso de caminhões, carretas, máquinas agrícolas, caminhões de entrega sem prévia autorização ou comunicação do associado.",
    "Capítulo V - 5.3: PORTARIA DE SERVIÇO - Carga/Descarga": "Regras específicas para o acesso de veículos de carga e descarga.",
    "Capítulo V - 5.3.1: Observações para veículos de carga": "O acesso de veículos de cargas, tais como caminhões, carretas, tratores, carroças ouquaisquer outros veículos que estejam carregados e cuja carga se destinem às unidades do RESIDENCIAL PARAÍSO DAS ÁGUAS deverão observar que:",
    "Capítulo V - 5.3.2: Identificação obrigatória do condutor": "Será obrigatória a identificação do condutor do veículo à segurança da portaria, segundo as normas estabelecidas para esse fim, além da confirmação do recebimento da mercadoria com local a que se destinar;",
    "Capítulo V - 5.3.3: Tempo de estacionamento (carga/descarga)": "Referidos veículos não poderão ficar estacionados nas ruas ou vias internas do RESIDENCIAL PARAÍSO DAS ÁGUAS, por tempo superior ao estritamente sufficiente para a carga ou descarga demercadorias;",
    "Capítulo V - 5.3.4: Orientação aos motoristas pela portaria": "Caberá ao responsável pela portaria orientar os motoristas dos veículos carregados quanto às regras de funcionamento interno do RESIDENCIAL PARAÍSO DAS Á GUAS, de forma a não alegarem ignorância delas;",
    "Capítulo V - 5.3.5: Horário para veículos de carga/descarga": "O horário de passagem dos veículos de carga/descarga será diariamente de 7 às 19 horas, não sendo permitido o pernoite de veículo que tenha entrado para descarregar e não tenharetornado;",
    "Capítulo V - 5.4: USO DAS ÁREAS COMUNS - Geral": "Define o que são áreas comuns e as regras gerais para seu uso racional e preservação.",
    "Capítulo V - 5.4.1: Definição de áreas comuns": "Compreendem-se por áreas comuns, aquelas que possam ser amplamente utilizadas por todos os moradores, sejam de lazer, de trânsito, de paisagismo ou para obras futuras do próprio RESIDENCIAL PARAÍSO DAS ÁGUAS. Para uso racional e preservacional dessas áreas, deverão ser obedecidas as seguintes regras de conduta:",
    "Capítulo V - 5.4.2: ÁREAS DE ESPORTE E LAZER": "Regulamenta o uso das quadras esportivas, playground e outras áreas de lazer.",
    "Capítulo V - 5.4.2.1: Livre acesso às quadras": "As quadras de esporte serão de livre acesso a todos os associados e seus convidados para a prática de esportes;",
    "Capítulo V - 5.4.2.2: Horário de funcionamento das quadras": "O horário de funcionamento das quadras será regulamentado em Resolução. da Diretoria e afixada na portaria;",
    "Capítulo V - 5.4.2.3: Responsabilidade pela conservação das quadras": "A família ou grupo que fizer uso das quadras terão responsabilidade pela sua conservação física enquanto ali permanecerem, cabendo-lhes inclusive arcar com eventuais despesas de recuperação de estragos provocados pelo mau uso;",
    "Capítulo V - 5.4.2.4: Fornecimento de material esportivo": "O RESIDENCIAL PARAÍSO DAS ÁGUAS poderá, a seu critério. Fornecer o material esportivo, que ficará sob estrita responsabilidade de quem o utilizar, cabendo-lhe devolver ao RESIDENCIAL PARAÍSO DAS ÁGUAS era perfeitas condições de uso:",
    "Capítulo V - 5.4.2.5: Controle de horários das quadras": "A administração do RESIDENCIAL PARAÍSO DAS AGUAS manterá um controle básico de horários de utilização das quadras, de forma a evitar conflitos de interesses entre osmoradores;",
    "Capítulo V - 5.4.2.6: Gratuidade no uso das quadras (exceto cursos)": "Não será cobrada nenhuma taxa ou aluguel pelo uso das quadras, salvo de empresasou profissionais que queiram explorar as quadras para cursos a serem oferecidos aos moradores;",
    "Capítulo V - 5.4.2.7: Uso do playground e áreas de lazer": "Os equipamentos infantis da área de lazer serão de uso exclusivo das crianças (playground), as crianças e adultos poderão brincar nas áreas de lazer sendo, todavia vedado Os jogos que possam por em risco a segurança das demais crianças e moradores;",
    "Capítulo V - 5.4.2.8: Horário da área de lazer": "A área de lazer ficará aberta ininterruptamente durante toda a semana no horário das 07h00 às 22h00;",
    "Capítulo V - 5.4.2.9: Acompanhamento de crianças (<7 anos)": "Não será permitida a presença de crianças com idade inferior a sete anos na área de lazer, sem que estejam acompanhadas por seu responsável;",
    "Capítulo V - 5.4.2.10: Proibição de brinquedos perigosos/perturbadores": "É proibida a utilização de qualquer brinquedo perigoso ou perturbador da boa ordem e sossego dos demais moradores;",
    "Capítulo V - 5.4.2.11: Conservação de brinquedos e equipamentos": "Os brinquedos e equipamentos existentes nos recintos de propriedade do RESIDENCIAL PARAÍSO DAS ÁGUAS deverão ser conservados em bom estado, ficando os associados e/ou responsáveis legais das crianças obrigados a ressarcir os danos por elas ocasionados nos brinquedos, aparelhos existentes ou equipamentos;",
    "Capítulo V - 5.4.2.12: Uso das quadras em/após chuva": "Será vedada a utilização das quadras de esporte e de areia, com chuva ou logo após, no intuito de evitar acidentes;",
    "Capítulo V - 5.4.2.13: Material esportivo/objetos abandonados": "Todo material esportivo que for deixado abandonado nas áreas de lazer, será recolhido e levado, sendo armazenado por um período de trinta dias, sendo que se o mesmo não for resgatado será doado para uma instituição de caridade; válido também para objetos de baixo valor perdido em eventos;",
    "Capítulo V - 5.4.2.14: Reservas das quadras esportivas": "As reservas das quadras esportivas deverão ser encaminhadas a administração com antecedência mínima de 24 horas e máxima de 5 dias, respeitando o horário de funcionamento da mesma.",
    "Capítulo V - 5.4.2.15: Uso preferencial pela administração": "A administração poderá dispor preferencialmente das quadras e demais áreas comuns para uso de atividades de interesse comum.",
    "Capítulo V - 5.4.2.16: Uso das churrasqueiras (Resolução)": "A utilização das churrasqueiras será disciplinadas por Resolução definida pela Diretoria e afixada na portaria.",

    "Capítulo V - 5.5: CRIAÇÃO DE ANIMAIS": "Regulamenta a permissão, proibição e condições para a criação e manutenção de animais no Residencial.",
    "Capítulo V - 5.5.1: Animais proibidos (silvestres, comerciais, etc.)": "Não será permitida ou tolerada, em nenhuma hipótese, a criação doméstica dos seguintes animais: animais silvestres (proibidos pelos órgãos de defesa do Meio Ambiente), animais com propósito de sua comercialização; animais ferozes: Animais exóticos e selvagens – ainda que domesticadas (por ex. búfalos, répteis, cobras, etc.); Animais mesmo que domesticados em nenhuma quantidade que coloque em perigo ou risco a comunidade local ou que perturbem o sossego (porcos, eqüinos, bovinos, caprinos). Animais em confinamento ou para engorda. Casos excepcionais (por exemplo: galinheiro) consultar a administração do RESIDENCIAL PARAÍSO DAS ÁGUAS;",
    "Capítulo V - 5.5.2: Raças caninas proibidas": "Fica proibida, ainda, a criação das seguintes raças caninas: Pitbull, Fila Brasileiro, Mastin Napolitano, Rotwailler e Doberman, além de outras que sejam conhecidamente violentas;",
    "Capítulo V - 5.5.3: Contenção de cães (médio/grande porte)": "Especialmente quando se tratar de cães de médio e grande porte, estes deverão ser contidos nas unidades individuais de forma a não se permitir sua fuga, e não perturbarem a ordem e instalações dos vizinhos, devendo toda a unidade ser isolada com cerca ou grade;",
    "Capítulo V - 5.5.4: Recolhimento de fezes": "As fezes produzidas pelos animais em locais de uso comum, deverão ser recolhidas pelo seu responsável e colocadas no lixo;",
    "Capítulo V - 5.5.5: Identificação e limite de animais (cães/gatos)": "Todos os felinos e caninos deverão ser identificados por coleira, contendo nomeendereço de seu proprietário, não sendo permitida a criação de mais de 4 (quatro) animais, entre caninos e felinos, por imóvel;",
    "Capítulo V - 5.5.6: Animais sem identificação (destino)": "Animais capturados sem identificação serão encaminhados ao centro de Zoonoses, salvo solução alternativa da administração do RESIDENCIAL PARAÍSO DAS ÁGUAS;",
    "Capítulo V - 5.5.7: Passeio com coleira e focinheira": "Todos os animais que estiverem passeando pelo RESIDENCIAL PARAÍSO DAS ÁGUAS devem estar acompanhados do criador e ainda presos a uma coleira, bem comopara as raças médias e grandes, usando focinheira. O trânsito de cães médios e grandes sem focinheira será considerado infração grave;",
    "Capítulo V - 5.5.8: Proibição de criação comercial": "Não será permitida a criação comercial de animais nas unidades autônomas.",
    "Capítulo V - 5.5.9: Responsabilidade por danos causados por animais": "O criador se responsabilizará pelos danos materiais e cíveis ocasionados por seus animais.",

    "Capítulo V - 5.6: ÁREA DE PRESERVAÇÃO PERMANENTE (APP)": "Define regras para a Área de Preservação Permanente (APP) que margeia o Lago Corumbá.",
    "Capítulo V - 5.6.1: Regras específicas para a APP": "A faixa legal de preservação que margeia o Lago Corumbá, internamente ao RESIDENCIAL PARAÍSO DAS ÁGUAS, é considerada Área de Preservação Permanente e para aquele local deverão ser observadas as seguintes regras:",
    "Capítulo V - 5.6.1.1: Proibição de fechar acesso à APP": "E terminantemente vedado aos associados vizinhos às vias marginais fecharem ou isolarem as passagens que acessem a APP, tanto para alongamento do seu terreno quanto para uso individual, devendo permanecer completamente desobstruídas as referidas vias:",
    "Capítulo V - 5.6.1.2: Responsabilidade pela conservação da orla": "Os associados, visitantes e prestadores de serviços serão inteiramente responsáveis pela conservação da orla, estando absolutamente proibidos de degradála de qualquer forma;",
    "Capítulo V - 5.6.1.3: Responsabilidade pela limpeza da orla": "Os associados, visitante e prestadores de serviços serão inteiramente responsáveis pela manutenção da limpeza da orla. devendo recolher todo o lixo que produzir, sendo vedado, ainda, deixar qualquer tipo de detrito seco ou orgânico (restos de comida, escamase vísceras de peixe, papéis, garrafas pet, embalagens, etc), evitando, assim, o aparecimento e proliferação de insetos e roedores.",

    "CAPÍTULO VI: REGULAMENTO DE CONSTRUÇÕES": "Estabelece as normas e procedimentos para a aprovação de projetos e execução de construções no Residencial.",
    "Capítulo VI - 6.1: DOS PROJETOS": "Define a Comissão de Obras, os tipos de construção permitidos e a necessidade de aprovação de projetos.",
    "Capítulo VI - 6.1.1: Comissão de Obras e Aprovação": "Será criada uma Comissão de Obras e Aprovação de Projetos composta por 01 (um) Presidente e 02 (dois) Conselheiros, que será responsável pela aprovação dos projetos e resolução dos casos omissos;",
    "Capítulo VI - 6.1.2: Tipos de construção proibidos": "Não será permitida a construção de prédios de apartamentos para habitação coletiva, bem como prédios para fins religiosos, comerciais e industriais, galpões ou outros que não sejam para fins exclusivamente de residências:",
    "Capítulo VI - 6.1.3: Modificação de projeto/obra": "Qualquer modificação ou acréscimo a ser feito no projeto ou na obra deverá sercomunicado previamente à administração da associação, apresentado o projeto para ser arquivado;",
    "Capítulo VI - 6.1.4: Padrões técnicos e profissionais habilitados": "Os padrões de construção deverão seguir orientação técnica no projeto e a execução sempre ter o acompanhamento de profissionais devidamente habilitados pelos Órgãos de Fiscalização.",
    "Capítulo VI - 6.1.5: Observância das plantas e memoriais": "A edificação a ser realizada sobre o bem imóvel adquirido, será construída com fiel observância das plantas aprovadas, das especificações do Memorial Descritivo que integram o Memorial de cada adquirente de terrenos, elaborados por especialistas na área de construção civil;",
    "Capítulo VI - 6.1.6: Proibição de desmembrar terreno": "E proibido ao proprietário desmembrar o terreno adquirido;",
    "Capítulo VI - 6.1.7: Construção de fossa séptica e sumidouro": "O associado deverá construir fossa séptica e sumidouro proporcional ao projeto de edificação, de acordo com a NBR número 7229 da ABNT, ou outra posterior que a substitua:",
    "Capítulo VI - 6.1.8: Submissão de projetos à Comissão": "Todos os projetos deverão ser submetidos a Comissão de Obras e Aprovação de Projetos.",

    "Capítulo VI - 6.2: DOS RECUOS": "Define as distâncias mínimas (recuos) que as edificações devem manter das divisas dos lotes.",
    "Capítulo VI - 6.2.1: Recuos obrigatórios (Frontal, Lateral, Fundo)": "A partir da data da aprovação deste regimento, quaisquer edificações deverão estar recuadas da seguinte forma: Frontal — 10 (dez) metros da testada do lote; Lateral: 02 (dois) metros das linhas divisórias. Fundo: 02 (dois) metros respeitando a reserva legal, com exceção dos lotes das quadras 7, 8 e 9 que deverão estar recuadas pelo menos a: Frontal — 6 (seis) metros da testada do lote; Lateral: 2,0 metros das linhas divisórias. Fundo – 2,0 metros respeitando a reserva legal.",
    "Capítulo VI - 6.2.1.1: Casos excepcionais (topografia)": "Casos excepcionais, em função da topografia do lote serão avaliados pela Comissão de Obras e Aprovação de Projetos, sendo vedada a aprovação de recuos frontais inferiores 05 (cinco) metros da testada do lote:",
    "Capítulo VI - 6.2.2.2: Uso da faixa de recuo frontal": "A faixa de recuo frontal poderá ser usada com jardim, ou qualquer outra edificação ao nível do solo, não podendo ter outra utilização, exceto estacionamento, assegurado sempre a livre circulação de veículos pelas vias de acesso do condomínio;",
    "Capítulo VI - 6.2.2.3: Impossibilidade de recuos (vistoria)": "Quando a topografia do terreno não permitir os recuos especificados acima o associado deverá apresentar requerimento de vistoria à administração para que esta certifique a impossibilidade dos referidos recuos e autorização para a construção da obra:",
    "Capítulo VI - 6.2.2.4: Fechamento frontal e lateral (muros/cercas)": "Não será permitida a construção de muros no fechamento frontal do lote, nem nas divisas laterais no trecho compreendido pelo recuo frontal, podendo, todavia, nestes trechos, ser construída cercas vivas até a altura de 1,80m ou poderá ser construída mureta de altura de 0,60m mais cercas e grades até a altura de 2,10m ou somente cercas e grades até a altura de 2,10 m.",
    "Capítulo VI - 6.2.2.5: Locação de piscina no recuo": "E permitida a locação de piscina sobre o recuo lateral ou de fundo com, no mínimo 2 (dois) metros da divisa. As piscinas deverão ser abastecidas por caminhão pipa:",
    "Capítulo VI - 6.2.3: Ponto de partida dos recuos": "Os recuos são sempre considerados a partir da demarcação do lote, inclusive quando se tratar de lote com servidão, ou seja, os recuos devem ser a partir do término da servidão ou reserva legal;",
    "Capítulo VI - 6.2.4: Recuos em lotes lindeiros (nascentes/APP)": "Para os lotes lindeiros às nascentes ou às zonas de proteção ambiental, deverá ser respeitado o limite definido pelo projeto urbanístico, desde que os recuos de divisa e frente sejam respeitados;",
    "Capítulo VI - 6.2.5: Uma entrada por unidade/rua": "Haverá apenas uma entrada destinada a cada unidade, por rua, não sendo permitida a subdivisão dos lotes, bem como habitações unifamiliares independentes;",
    "Capítulo VI - 6.2.6: Taludes e movimentação de terra": "Taludes de acertos de movimentação de terra, aterros ou cortes, devem respeitar o item 3.8 acima, devendo o interessado comunicar previamente à administração da associação para sua avaliação e posterior aprovação;",
    "Capítulo VI - 6.2.7: Modificação topográfica (nascentes/águas pluviais)": "A modificação topográfica do terreno deverá preservar as nascentes existentes bem como o curso das águas pluviais, de forma natural ou artificial, evitando-se o transbordo excessivo para as vias de rolamento;",
    "Capítulo VI - 6.2.8: Arrimo em recuos (limites)": "E permitido o arrimo em recuos laterais e de fundo desde que obedeça a um afastamento mínimo da divisa de 2 metros, uma altura máxima de 1,5 metro para aterro e profundidade máxima de 1,5 metro para corte, respeitando ainda uma extensão máxima de 15% com relação à divisa em questão, exceto para os locais que já receberam tubulações de infra-estrutura. No recuo frontal de 6 metros, após os 3 metros iniciais, O arrimo será permitido apenas para rampas de acessos de subsolos e para acessos de pedestres, nos 3metrosrestantes;",
    "Capítulo VI - 6.2.9: Áreas de secagem de roupas (localização/vedação)": "As áreas de secagem de roupas deverão ser voltadas para as laterais ou fundo doslotes. Para tanto, é permitida a colocação de elemento vazado nos recuos laterais e de fundo, exclusivamente para a vedação das áreas de secagem de roupas, podendo ser utilizados blocos de elemento vazado, grades, treliças de madeira ou tijolo intercalado (não excedendo a 50% de vedação), devendo obedecer à distância mínima da divisa de 2 (dois) metros, altura máxima de 2 (dois) metros e uma extensão máxima de 5 (cinco) metros, com recuo mínimo de 20 metros frontais, exceto para os locais que já receberam tubulações de infra-estrutura;",
    "Capítulo VI - 6.2.10: Número máximo de pavimentos e altura": "Nenhuma edificação deverá ter mais de dois pavimentos, obedecendo-se uma altura máxima da edificação de 7,60 metros;",
    "Capítulo VI - 6.2.11: Subsolo (definição e permissão)": "A existência de subsolo (ambientes totalmente sob a linha natural da rua) é permitida, devendo observar as normas municipais do código de edificações e o uso do solo. Quando houver, pelo aproveitamento do caimento do terreno. a existência de um nível inferior a dois pavimentos, não sendo considerado um 3º pavimento;",
    "Capítulo VI - 6.2.12: Vedação dos lotes (materiais e altura)": "A vedação dos lotes poderá ser feita de vidros, cerca viva, cerca colonial, alambrados e alvenarias, sendo que, neste último caso, deverá ser utilizada em conjunto com os demais materiais de forma que a alvenaria limite-se a ao máximo de 0,60m de altura, a partir da qual deverá ser utilizados os materiais anteriormente citados. A altura máxima das vedações é de 2,1m respeitando-se o determinado no item 6.2.2.4.",
    "Capítulo VI - 6.2.13: Cercas vivas (recuo e manutenção)": "As covas de cercas vivas devem ser recuadas de no mínimo 0,5 (meio) metro da linha divisória, ficando a manutenção e poda a cargo do proprietário que a plantou.",

    "Capítulo VI - 6.3: NORMAS DE OBRAS": "Estabelece regras específicas para a condução e execução das obras.",
    "Capítulo VI - 6.3.1: Autorização para início da obra": "O início da obra será autorizado pela associação, somente após o recebimento e a aprovação do projeto;",
    "Capítulo VI - 6.3.2: Retirada de cartilha de orientações": "Antes do início da obra, o interessado deverá retirar junto à Comissão de Obras e Aprovação de Projetos, uma cartilha com os dados atualizados de ligações e abastecimentos entre outros, referentes ao caso específico de cada lote e importantes para o início dos trabalhos de construção;",
    "Capítulo VI - 6.3.3: Retirada de árvore (replantio)": "No caso da necessidade de retirada de árvore para implantação de construções, sugere-se o replantio pelo associado, na proporção mínima de duas para uma, sendo que as espécies e localização de plantio serão definidas em conjunto com aassociação:",
    "Capítulo VI - 6.3.4: Instalações provisórias (barracão)": "As instalações provisórias nos barracões de obra deverão ser executadas antes do início efetivo da obra;",
    "Capítulo VI - 6.3.5: Depósito de materiais e restos de obra": "O depósito e a colocação de materiais sempre deverá ocorrer dentro dos limites do lote e os restos de obras devem ser acondicionados em locais apropriados, posicionados.",
    "Capítulo VI - 6.3.6: Acesso à obra (proibições)": "E vedado o acesso à obra por áreas verdes e de lazer, por lotes vizinhos sem autorização de seu proprietário ou em desacordo com o código municipal de posturas;",
    "Capítulo VI - 6.3.7: Barracão de obra (higiene e localização)": "O barracão, com recuo de no mínimo 05 (cinco) metros frontais, deve atentar para as condições de higiene e limpeza, não podendo estar posicionado junto à divisa do morador;",
    "Capítulo VI - 6.3.8: Responsabilidade por danos (obra)": "O proprietário ou titular de direito da construção que estiver executando a obra, responderá perante a associação, e perante terceiros pelos eventuais danos causados, direta ou indiretamente, pela utilização de betoneiras, escavadeiras, guindastes, bate-estacas ou outros equipamentos empregados na obra, inclusive por acidentes que ocorrerem com pessoas que ali transitarem;",
    "Capítulo VI - 6.3.9: Paralisação da obra (procedimentos)": "Havendo motivo de força maior para a paralisação da obra, tal fato deverá ser comunicado à associação, ficando o proprietário obrigado a: Remover ou acondicionar adequadamente de restos de materiais oudetritos; Restaurar o passeio na frente do lote; Fechar os acessos à obra de forma a não permitir ingresso de pessoas estranhas, no prazo máximo de 15 dias. O descumprimento do disposto neste item, após a competente notificação por escrito feita ao proprietário ou preposto, implicará na tomada de providência em seu nome, sendo que os serviços acima executados serão cobrados posteriormente do proprietário, com acréscimos e penalidades aprovadas em assembléia;",
    "Capítulo VI - 6.3.10: Fiscalização da obra pela associação": "À associação fiscalizará a execução da obra de acordo com o projeto aprovado, e se achar divergências poderá embargar administrativamente a obra, denunciando ao poder público municipal;",
    "Capítulo VI - 6.3.11: Irregularidades na obra (notificação/prazo)": "Deverão ser obedecidos todos os itens normatizados neste regulamento interno e caso a associação, encontre irregularidades, será estabelecido um prazo para a regularização, correção ou reparo, através de notificação ao proprietário ou seu preposto. Diante do não cumprimento, a associação, aplicará as penalidades previstas e ainda poderá tomar as providências e repassar os custos aos proprietários;",
    "Capítulo VI - 6.3.12: Edificações preexistentes": "As edificações já existentes, antes da aprovação do presente regimento interno, serão consideradas válidas para todos os efeitos, desde que tenham sido respeitadas as normas constantes do contrato de compra e venda realizado com a JMD EmpreendimentoImobiliários e que seguirá em anexo ao presente Regimento para fins de consulta;",
    "Capítulo VI - 6.3.13: Avaliação estética dos projetos": "Os projetos submetidos a Comissão de Obras e Aprovação de Projetos serão avaliados Segundo o tipo de material, forma e aspectos arquitetônicos, visando a manutenção da estética geral do RESIDENCIAL PARAÍSO DAS ÁGUAS.",

    "Capítulo VI - 6.4: DAS CALÇADAS": "Define as regras e padrões para a construção e manutenção das calçadas.",
    "Capítulo VI - 6.4.1: Obrigatoriedade das calçadas (após pavimentação)": "A confecção das calçadas não será obrigatória até a pavimentação das vias internas do RESIDENCIAL PARAÍSO DAS ÁGUAS.",
    "Capítulo VI - 6.4.2: Padrão de calçamento (opcional)": "As unidades que optarem por realizá-las terá que seguir um padrão de calçamento observando o limite de até 1,5 (um metro e meio) frente à unidade e respeitando a permeabilização com um limite de até 75cm do uso de pedra pirenópolis com grama ou bloquetes “pavers” com grama e o restante com a grama “esmeralda” na frente, ou somente grama em sua totalidade.",
    "Capítulo VI - 6.4.2: Manutenção das calçadas (proprietário)": "As calçadas devem ser construídas e terem sua manutenção por conta do proprietário da unidade.",
    "Capítulo VI - 6.4.2: Construção plana da calçada (1,5m)": "A calçada será construída de forma plana medindo 1,5 (um metro e meio) dos limites de demarcação do lote;",
    "Capítulo VI - 6.4.2: Não obrigatoriedade (até pavimentação)": "A construção da calçada não é obrigatória até definir a pavimentação da rua;",
    "Capítulo VI - 6.4.2: Requisitos ao optar por construir": "Optando por construir a calçada está terá a obrigatoriedade de seguir os seguintes requisitos: medindo dos limites de demarcação frontal da unidade em direção a rua 75 cm em pedra pirenópolis com grama ou bloquetes/pavers com grama, ou somente grama. Os últimos 75cm serão complementados com grama “esmeralda”;",
    "Capítulo VI - 6.4.2: Recuperação após patrolamento": "Os proprietários se comprometem a recuperar os respectivos passeios/calçadas caso ocorra algum tipo de ajuste no patrolamento das ruas;",
    "Capítulo VI - 6.4.2: Manutenção da grama (notificação/taxa)": "No caso de utilização de grama se a unidade não providenciar a manutenção a Associação fará um notificação/comunicado para o responsável fazê-lo, não ocorrendo à devida manutenção após a notificação/ comunicado será documentado (fotos) e associação providenciará a limpeza cobrando uma taxa ordinária de contribuição mensal.",

    "ANEXO IV: COMISSÃO DE FESTAS E EVENTOS": "Define a criação, composição e atribuições da Comissão de Festas e Eventos.",
}

# --- Funções Auxiliares ---

def sanitize_key(key_text):
    """Gera uma chave segura para widgets Streamlit."""
    sanitized = re.sub(r'[^\w\s-]', '', key_text).strip()
    sanitized = re.sub(r'\s+', '_', sanitized)
    return sanitized.lower()[:50]

@st.cache_data
def convert_df_to_csv(df):
    """Converte DataFrame para CSV para download."""
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# --- Conexão com Google Sheets (Cacheada) ---

# Escopos necessários para a API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

@st.cache_resource
def init_connection():
    """
    Inicializa a conexão com a Google Sheets API, aceitando:
    1) [gcp_service_account] em secrets TOML,
    2) GOOGLE_CREDENTIALS_JSON (string JSON ou dict) em secrets,
    3) arquivo local google_credentials.json (para dev).
    """
    sa_info = None
    source = None

    try:
        # 1) Tabela TOML: [gcp_service_account]
        if "gcp_service_account" in st.secrets:
            sa_info = dict(st.secrets["gcp_service_account"])
            source = "secrets: gcp_service_account"

        # 2) JSON em string/dict: GOOGLE_CREDENTIALS_JSON
        elif "GOOGLE_CREDENTIALS_JSON" in st.secrets:
            raw = st.secrets["GOOGLE_CREDENTIALS_JSON"]
            if isinstance(raw, str):
                sa_info = json.loads(raw)
            elif isinstance(raw, dict):
                sa_info = dict(raw)
            else:
                st.error("GOOGLE_CREDENTIALS_JSON encontrado, mas em formato não suportado.")
                return None
            source = "secrets: GOOGLE_CREDENTIALS_JSON"

        # 3) Arquivo local para desenvolvimento
        elif os.path.exists("google_credentials.json"):
            with open("google_credentials.json", "r", encoding="utf-8") as f:
                sa_info = json.load(f)
            source = "arquivo local google_credentials.json"
        else:
            st.error("Credenciais não encontradas. Configure secrets ou inclua google_credentials.json.")
            return None

        # Normaliza quebras de linha da private_key
        if "private_key" in sa_info and isinstance(sa_info["private_key"], str):
            sa_info["private_key"] = sa_info["private_key"].replace("\\n", "\n")

        creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        st.toast(f"Conectado com credenciais ({source}).", icon="🔐")
        return client

    except json.JSONDecodeError as e:
        st.error(f"Credenciais JSON inválidas: {e}")
    except Exception as e:
        st.error(f"Falha ao autorizar conexão com Google Sheets: {e}")

    return None

def get_worksheet(client):
    """Obtém a worksheet específica."""
    if client is None:
        return None
    try:
        spreadsheet = client.open(GOOGLE_SHEET_NAME)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        return worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Planilha '{GOOGLE_SHEET_NAME}' não encontrada. Verifique o nome e as permissões de compartilhamento.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Aba/Worksheet '{WORKSHEET_NAME}' não encontrada na planilha '{GOOGLE_SHEET_NAME}'.")
        return None
    except Exception as e:
        st.error(f"Erro ao acessar a planilha/worksheet: {e}")
        return None

# --- Inicializa a conexão ---
gspread_client = init_connection()

# --- Funções para Interagir com a Planilha ---

def write_feedback_to_sheet(worksheet, feedback_data):
    """Escreve uma nova linha de feedback na planilha."""
    if worksheet is None:
        st.error("Não foi possível escrever na planilha (conexão não estabelecida).")
        return False
    try:
        row_to_insert = [
            feedback_data.get("Item Revisado (com Descrição)", ""),
            feedback_data.get("Remetente", ""),
            feedback_data.get("Crítica/Comentário", ""),
            feedback_data.get("Sugestão de Alteração", ""),
            feedback_data.get("Data/Hora", "")
        ]
        worksheet.append_row(row_to_insert, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Erro ao escrever na planilha: {e}")
        return False

@st.cache_data(ttl=600)
def read_feedback_from_sheet(_worksheet):
    """Lê todos os dados de feedback da planilha."""
    if _worksheet is None:
        st.error("Não foi possível ler da planilha (conexão não estabelecida).")
        return pd.DataFrame()
    try:
        data = _worksheet.get_all_records()
        df = pd.DataFrame(data)
        expected_cols = ["Item Revisado (com Descrição)", "Remetente", "Crítica/Comentário", "Sugestão de Alteração", "Data/Hora"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        df = df[expected_cols]
        return df
    except Exception as e:
        st.error(f"Erro ao ler dados da planilha: {e}")
        return pd.DataFrame()

# --- Interface do Streamlit ---

st.title("✍️ Ferramenta de Revisão do Regimento Interno")
st.markdown("""
Bem-vindo(a), associado(a) do Residencial Paraíso das Águas!

Utilize esta ferramenta para revisar o **Regimento Interno (2ª Alteração - Nov/2019)**,
item por item. Selecione um item na lista abaixo para ver seu texto completo e
enviar suas críticas e sugestões. Sua participação é fundamental!
""")
st.markdown("---")

# --- Seleção do Item ---
lista_itens_com_hints = list(regimento_com_hints.keys())
item_selecionado_com_hint = st.selectbox(
    "Selecione o Capítulo / Item / Anexo que deseja revisar:",
    lista_itens_com_hints,
    index=None,
    placeholder="Escolha um item pela descrição..."
)

st.markdown("---")

# --- Exibição do Item e Campos de Feedback ---
if item_selecionado_com_hint:
    safe_key_base = sanitize_key(item_selecionado_com_hint)
    form_key = f"form_{safe_key_base}"
    texto_key = f"texto_{safe_key_base}"
    remetente_key = f"remetente_{safe_key_base}"

    st.subheader(f"Item Selecionado: {item_selecionado_com_hint}")
    texto_item = regimento_com_hints.get(item_selecionado_com_hint, "*Item não encontrado nos dados carregados.*")
    st.text_area(
        "Texto Completo / Descrição Detalhada:",
        value=texto_item,
        height=250,
        disabled=True,
        key=texto_key
    )

    st.markdown("---")
    st.subheader("📩 Seu Feedback sobre este Item:")

    worksheet = get_worksheet(gspread_client)

    with st.form(key=form_key):
        critica = st.text_area(
            "Críticas / Comentários / Justificativas:",
            height=100,
            placeholder="Descreva aqui os pontos que você acha que precisam de mudança, ou os problemas com a redação atual."
        )
        sugestao = st.text_area(
            "Sugestão de Nova Redação / Alteração:",
            height=100,
            placeholder="Se tiver uma sugestão de como o texto deveria ficar, escreva aqui."
        )
        remetente = st.text_input(
            "Sua Identificação (Nome / Unidade - Opcional):",
            key=remetente_key,
            placeholder="Ex: João Silva / Lote 10 Quadra 5"
        )

        submitted = st.form_submit_button("✔️ Enviar Feedback para Google Sheet")

        if submitted:
            if not worksheet:
                st.error("Falha na conexão com a Planilha. Feedback não pode ser enviado.")
            elif not critica and not sugestao:
                st.warning("Por favor, escreva ao menos uma crítica ou sugestão antes de enviar.")
            else:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                feedback_data = {
                    "Item Revisado (com Descrição)": item_selecionado_com_hint,
                    "Remetente": remetente if remetente else "Anônimo",
                    "Crítica/Comentário": critica,
                    "Sugestão de Alteração": sugestao,
                    "Data/Hora": timestamp
                }
                success = write_feedback_to_sheet(worksheet, feedback_data)
                if success:
                    st.success(f"✅ Feedback para '{item_selecionado_com_hint}' enviado com sucesso para a Planilha Google! Obrigado.")
                else:
                    st.error("❌ Houve um erro ao tentar salvar seu feedback na Planilha. Tente novamente mais tarde.")

# --- Seção de Administração (Protegida por Senha) ---
st.markdown("---")
st.header("🔒 Área Administrativa - Feedback Consolidado")

correct_password = st.secrets.get("ADMIN_PASSWORD", "senha_padrao_local")

password_attempt = st.text_input("Digite a senha de administrador para ver o feedback:", type="password", key="admin_password_input")

if password_attempt:
    if password_attempt == correct_password:
        st.success("Senha correta! Acessando dados...")
        worksheet_admin = get_worksheet(gspread_client)

        if worksheet_admin:
            st.subheader("📊 Resumo do Feedback Recebido (da Planilha)")
            df_feedback = read_feedback_from_sheet(worksheet_admin)

            if not df_feedback.empty:
                st.dataframe(df_feedback, use_container_width=True)

                csv_data = convert_df_to_csv(df_feedback)
                st.download_button(
                    label="📥 Baixar Feedback Completo (CSV)",
                    data=csv_data,
                    file_name=f"feedback_regimento_interno_{datetime.date.today()}.csv",
                    mime="text/csv",
                    key="download_csv_button"
                )
            else:
                st.info("Ainda não há feedback registrado na planilha ou houve erro na leitura.")
        else:
            st.error("Não foi possível conectar à planilha para buscar o feedback.")
    else:
        st.error("Senha incorreta.")

# Mensagem final
st.markdown("---")
st.caption(f"Regimento Interno - 2ª Alteração (Base: Documento de Nov/2019). Conectado à Google Sheet '{GOOGLE_SHEET_NAME}'.")
