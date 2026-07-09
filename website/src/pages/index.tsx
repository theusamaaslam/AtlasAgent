import React from 'react';
import clsx from 'clsx';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './index.module.css';

const capabilities = [
  {
    title: 'Summary-first memory',
    detail:
      'Atlas preserves raw sessions, distills clean 200-word summaries, promotes durable facts, and recalls only the most relevant evidence before answering.',
  },
  {
    title: 'Visual knowledge graph',
    detail:
      'Facts, summaries, topics, entities, projects, and creator profile nodes form a searchable graph that grows as the agent works.',
  },
  {
    title: 'CLI, TUI, and dashboard',
    detail:
      'Use the same agent core from the terminal, embedded TUI dashboard, or always-on server interface without splitting conversations.',
  },
  {
    title: 'Tools and real execution',
    detail:
      'File edits, terminal commands, web actions, scheduled jobs, browsers, model routing, and MCP connectors are available through one operator surface.',
  },
  {
    title: 'Skills that compound',
    detail:
      'Atlas turns repeated workflows into reusable skills and keeps procedural knowledge close to the agent instead of hidden in a chat log.',
  },
  {
    title: 'Runs where you need it',
    detail:
      'Local machine, VPS, Docker, SSH, Modal, Daytona, and messaging gateway deployments are all first-class ways to keep the agent online.',
  },
];

const memoryFlow = [
  'USER.md and MEMORY.md anchor durable identity and operating preferences.',
  'Approved facts and compact summaries answer most recall needs.',
  'Raw session archive stays searchable as fallback evidence.',
  'Conflicts are surfaced for correction instead of silently overwriting truth.',
];

const deploySteps = [
  ['Clone', 'git clone https://github.com/theusamaaslam/AtlasAgent.git'],
  ['Install', 'bash scripts/install.sh'],
  ['Configure', 'atlas setup'],
  ['Dashboard', 'atlas dashboard --host 0.0.0.0 --port 9119 --no-open'],
];

function TerminalPanel() {
  return (
    <div className={styles.terminalPanel} aria-label="Atlas terminal preview">
      <div className={styles.terminalTopline}>
        <span>atlas</span>
        <span>memory online</span>
      </div>
      <pre>
        {`$ atlas

ATLAS AGENT
Created by Usama Aslam

> memory recall "dashboard design"
facts       4 ranked results
summaries   3 compact notes
archive     ready as fallback

> atlas dashboard --port 9119
Dashboard ready on http://0.0.0.0:9119`}
      </pre>
      <div className={styles.graphPreview}>
        <span className={styles.nodeCreator}>Creator</span>
        <span className={styles.nodeFact}>Fact</span>
        <span className={styles.nodeSummary}>Summary</span>
        <span className={styles.nodeTopic}>Topic</span>
        <span className={styles.nodeProject}>Project</span>
      </div>
    </div>
  );
}

export default function Home(): React.ReactNode {
  const banner = useBaseUrl('/img/atlas-agent-banner.png');

  return (
    <Layout
      title="Atlas Agent"
      description="Atlas Agent is a self-improving AI agent created by Usama Aslam with memory, skills, tools, dashboard, and production deployment support."
    >
      <main className={styles.page}>
        <section className={styles.hero}>
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>Created by Usama Aslam</p>
            <h1>Atlas Agent</h1>
            <p className={styles.lede}>
              A self-improving AI agent for operators who want memory that compounds, skills that
              evolve, and a dashboard that makes the agent understandable while it works.
            </p>
            <div className={styles.actions}>
              <Link className={clsx(styles.button, styles.primary)} to="/getting-started/installation">
                Install Atlas
              </Link>
              <Link className={clsx(styles.button, styles.secondary)} to="/getting-started/quickstart">
                Read the docs
              </Link>
              <a className={clsx(styles.button, styles.ghost)} href="https://github.com/theusamaaslam/AtlasAgent">
                GitHub
              </a>
            </div>
          </div>
          <div className={styles.heroVisual}>
            <img src={banner} alt="Atlas Agent banner" />
            <TerminalPanel />
          </div>
        </section>

        <section className={styles.strip} aria-label="Atlas highlights">
          <div>
            <strong>Memory V2.5</strong>
            <span>summary-first recall</span>
          </div>
          <div>
            <strong>Production dashboard</strong>
            <span>port 9119 ready</span>
          </div>
          <div>
            <strong>Local-first</strong>
            <span>SQLite, FTS, optional embeddings</span>
          </div>
          <div>
            <strong>White-label</strong>
            <span>Atlas by Usama Aslam</span>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.eyebrow}>Why Atlas</p>
            <h2>Built around useful memory, not bigger prompts.</h2>
            <p>
              Atlas logs interactions, summarizes them, extracts high-value facts, and retrieves the
              smallest useful context when the current request needs history.
            </p>
          </div>
          <div className={styles.capabilityGrid}>
            {capabilities.map((item) => (
              <article className={styles.card} key={item.title}>
                <h3>{item.title}</h3>
                <p>{item.detail}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={clsx(styles.section, styles.memorySection)}>
          <div className={styles.memoryCopy}>
            <p className={styles.eyebrow}>Agent-useful memory</p>
            <h2>The graph is the visible layer. Retrieval is the useful layer.</h2>
            <p>
              USER.md and MEMORY.md stay the first source of truth. Approved facts and compact
              summaries come next. Raw sessions remain preserved, searchable, and available only when
              curated memory cannot answer the question.
            </p>
            <Link className={clsx(styles.button, styles.secondary)} to="/user-guide/features/memory">
              Memory documentation
            </Link>
          </div>
          <div className={styles.memoryStack}>
            {memoryFlow.map((step, index) => (
              <div className={styles.memoryStep} key={step}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <p>{step}</p>
              </div>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.eyebrow}>Production path</p>
            <h2>Clone, configure, and run the dashboard.</h2>
            <p>
              The public repo includes the installer and deployment scripts. GitHub Pages publishes
              this documentation from the same source tree.
            </p>
          </div>
          <div className={styles.deployGrid}>
            {deploySteps.map(([label, command]) => (
              <div className={styles.deployStep} key={label}>
                <span>{label}</span>
                <code>{command}</code>
              </div>
            ))}
          </div>
        </section>
      </main>
    </Layout>
  );
}
