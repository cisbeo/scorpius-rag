# CONTEXTE PROJET SCORPIUS RAG

## 🎯 MISSION & OBJECTIF

**Scorpius** est un système RAG (Retrieval-Augmented Generation) spécialisé dans l'analyse d'appels d'offres publics français. L'objectif est d'augmenter significativement le win rate des ESN sur les marchés publics en automatisant et optimisant le processus d'analyse et de réponse.

## 🏢 CONTEXTE MÉTIER

### Domaine d'Application

- **Marchés publics français** : État, Collectivités territoriales, Secteur hospitalier, EPA/EPIC
- **Procédures** : MAPA, Appels d'offres ouverts/restreints, Dialogue compétitif
- **Montants** : 10k€ à 50M€+ avec adaptation formalisme
- **Secteurs techniques** : IT, Digital, Conseil, Ingénierie

### Utilisateurs Cibles

- **Ingénieurs d'affaires** en ESN
- **Directeurs commerciaux**
- **Chefs de projet** réponse AO
- **Équipes business development**

### Pain Points Adressés

1. **Temps d'analyse DCE** : 2-3 jours → 2-3 heures
2. **Qualification opportunités** : Intuition → Scoring objectif /100
3. **Intelligence concurrentielle** : Approximative → Données factuelles
4. **Conformité réglementaire** : Erreurs fréquentes → Validation automatique
5. **Templates mémoires** : Réinvention → Réutilisation optimisée

## 🔧 ARCHITECTURE TECHNIQUE

### Stack Technologique

- **Backend** : Python 3.9+ avec async/await
- **RAG Engine** : ChromaDB (vector database) + métadonnées structurées  
- **IA Services** : OpenRouter API (multi-modèles) + OpenAI fallback
- **Frontend** : Streamlit (interface web professionnelle)
- **Déploiement** : Docker + Kubernetes + CI/CD

### Modèles IA Optimaux

- **Embeddings** : `voyage-large-2-instruct` (performance FR + économique)
- **Génération** : `claude-3.5-sonnet` (analyse), `claude-3-haiku` (rapide), `gpt-4o` (calculs)
- **Fallback** : OpenAI `text-embedding-3-large` + `gpt-4-turbo`

### Base de Connaissances RAG

1. **Réglementaire** (conformité bulletproof)
   - Code des marchés publics (articles, jurisprudence)
   - CCAG-TIC, CCAG-PI, CCAG-FCS par secteur
   - Seuils européens (maj automatique)
   - Normes ANSSI, ISO, HDS, RGPD secteur public

2. **Historique AO** (intelligence competitive)
   - Résultats BOAMP/TED (web scraping automatisé)
   - Analyses post-attribution (prix, concurrent gagnant, causes)
   - Patterns sectoriels (critères pondération, délais, spécificités)
   - Base concurrents (stratégies, forces/faiblesses, grilles prix)

3. **Références Clients** (crédibilisation)
   - Projets similaires détaillés (contexte, solution, résultats)
   - Retours satisfaction quantifiés
   - Contacts référents vérifiables
   - Cas d'usage par secteur/technologie

4. **Templates Performants** (accélération rédaction)
   - Mémoires techniques gagnants (par secteur/type AO)
   - Sections réutilisables (executive summary, méthodologie, etc.)
   - Arguments différenciateurs éprouvés
   - Structures optimales selon pondération critères

5. **Intelligence Concurrentielle** (avantage tactique)
   - Profils détaillés concurrents (Tier 1, Tier 2, Pure players)
   - Historique victoires/défaites par concurrent
   - Stratégies prix et positionnement
   - Partenariats et certifications récentes

## 🎯 FONCTIONNALITÉS CORE

### 1. Qualification AO Intelligente

- **Input** : Description AO + DCE (si disponible)
- **Process** : Analyse automatique critères, budget, concurrence, fit compétences
- **Output** : Score qualification /100 + recommandation GO/NO-GO + stratégie

### 2. Analyse DCE Enrichie  

- **Input** : Documents consultation (PDF, Word, TXT)
- **Process** : Extraction critères + pondération, recherche contexte RAG, analyse risques
- **Output** : Synthèse executive + axes différenciation + estimation prix cible

### 3. Génération Mémoire Technique

- **Input** : Contexte AO + templates disponibles + contraintes
- **Process** : Structuration optimale + réutilisation sections performantes + adaptation
- **Output** : Mémoire technique structuré + checklist conformité

### 4. Intelligence Concurrentielle

- **Input** : Secteur + montant + type AO
- **Process** : Prédiction concurrents probables + analyse stratégies + benchmarking prix
- **Output** : Positionnement optimal + arguments anti-concurrence

### 5. Conformité Automatique

- **Input** : Dossier réponse complet
- **Process** : Vérification exhaustive vs réglementation + checklist secteur
- **Output** : Rapport conformité + actions correctives + niveau risque

## 📊 MÉTRIQUES SUCCESS

### KPIs Business (Objectifs)

- **Win Rate** : +20-30% vs baseline actuelle
- **Temps analyse** : -40% (3 jours → 4 heures)
- **Conformité** : 95%+ validation réglementaire  
- **ROI** : 500%+ première année d'usage
- **Satisfaction** : 4.5+/5 utilisateurs

### KPIs Techniques (Performance)

- **Temps réponse** : <2s analyse standard, <5s analyse complexe
- **Précision RAG** : 80%+ pertinence contexte récupéré
- **Disponibilité** : 99.5%+ uptime système
- **Coût IA** : <2€ par analyse complète d'AO
- **Évolutivité** : Support 100+ utilisateurs simultanés

## 🚀 ROADMAP ÉVOLUTION

### Phase 1 (MVP - 6 semaines)

- RAG engine fonctionnel 4 collections
- Interface Streamlit essentielle
- Analyse AO basique + templates
- Conformité réglementaire de base

### Phase 2 (Optimisation - 4 semaines)  

- Intelligence concurrentielle avancée
- Scraping automatisé BOAMP/TED
- Export PDF/Word professionnel
- APIs plateformes dématérialisées

### Phase 3 (Enterprise - 6 semaines)

- Multi-tenant + authentification
- Workflow collaboratif équipes
- Intégrations CRM/ERP entreprise
- Analytics avancées + reporting

### Phase 4 (IA Avancée - 8 semaines)

- Agent autonome veille AO
- ML prédictif win probability  
- NLP analyse sentiment DCE
- Recommandations pricing dynamiques

## 🔒 CONTRAINTES & EXIGENCES

### Sécurité & Confidentialité

- **RGPD compliance** : Données clients anonymisées
- **Chiffrement** : At-rest et in-transit
- **Audit trail** : Toutes opérations loggées
- **Accès contrôlé** : Authentification + autorisation granulaire

### Performance & Scalabilité

- **Latence** : <2s réponse utilisateur standard
- **Throughput** : 1000+ requêtes/heure soutenues  
- **Élasticité** : Auto-scaling selon charge
- **Backup** : Sauvegarde quotidienne + récupération <4h

### Intégration & Maintenance

- **APIs** : REST + webhooks pour intégrations
- **Monitoring** : Métriques business + techniques temps réel
- **CI/CD** : Déploiement automatisé + rollback
- **Documentation** : À jour automatiquement + guides utilisateur
