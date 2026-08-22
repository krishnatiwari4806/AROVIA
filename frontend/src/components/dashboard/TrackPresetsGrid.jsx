import React from 'react';
import { Layers, Server, Code2, Cloud, Cpu, Database, UserCheck, ArrowRight, Sparkles } from 'lucide-react';

const TRACK_ICONS = {
  'backend-engineer': Server,
  'frontend-engineer': Code2,
  'fullstack-engineer': Layers,
  'devops-cloud-engineer': Cloud,
  'data-engineer': Database,
  'ml-engineer': Cpu,
  'behavioral': UserCheck,
};

/**
 * Role Track Selection & Quick Preset Cards.
 */
export function TrackPresetsGrid({ presets, onSelectPreset }) {
  const roles = presets?.roles || [
    {
      role_id: 'fullstack-engineer',
      title: 'Fullstack Engineer',
      description: 'End-to-end web architectures, React frontend state, async REST/GraphQL APIs, and relational modeling.',
      default_skills: ['React', 'Node.js', 'Python', 'SQL', 'REST APIs', 'Docker'],
      recommended_seniority: ['junior', 'mid', 'senior'],
    },
    {
      role_id: 'backend-engineer',
      title: 'Backend Engineer',
      description: 'Distributed services, database scalability, async ASGI frameworks, API design, and query optimization.',
      default_skills: ['Python', 'FastAPI', 'PostgreSQL', 'Redis', 'Docker', 'Microservices'],
      recommended_seniority: ['junior', 'mid', 'senior'],
    },
    {
      role_id: 'frontend-engineer',
      title: 'Frontend Engineer',
      description: 'Modern component design, state managers, DOM performance, CSS architectures, and browser audio/visual APIs.',
      default_skills: ['React', 'TypeScript', 'JavaScript', 'CSS3', 'Vite', 'Web Performance'],
      recommended_seniority: ['junior', 'mid', 'senior'],
    },
    {
      role_id: 'devops-cloud-engineer',
      title: 'DevOps / Cloud Engineer',
      description: 'Container orchestration, CI/CD pipelines, Infrastructure as Code, reliability, and security practices.',
      default_skills: ['AWS', 'Docker', 'Kubernetes', 'Terraform', 'CI/CD', 'Linux'],
      recommended_seniority: ['junior', 'mid', 'senior'],
    },
    {
      role_id: 'data-engineer',
      title: 'Data Engineer',
      description: 'Large-scale ETL pipelines, streaming architectures, data lakes, warehousing, and schema migrations.',
      default_skills: ['Python', 'SQL', 'Apache Spark', 'Kafka', 'ETL Pipelines', 'PostgreSQL'],
      recommended_seniority: ['junior', 'mid', 'senior'],
    },
    {
      role_id: 'ml-engineer',
      title: 'Machine Learning Engineer',
      description: 'Applied ML systems, deep learning architectures, prompt engineering, LLM fine-tuning, and MLOps.',
      default_skills: ['Python', 'PyTorch', 'TensorFlow', 'LLMs', 'MLOps', 'Vector DBs'],
      recommended_seniority: ['junior', 'mid', 'senior'],
    },
  ];

  return (
    <div className="section-container">
      <div className="section-header-row">
        <div>
          <h2 className="section-title">Curated Technical Tracks</h2>
          <p className="section-subtitle">Select a target role track calibrated with industry-standard question sets and rubrics.</p>
        </div>
      </div>

      <div className="tracks-grid">
        {roles.map((role) => {
          const IconComponent = TRACK_ICONS[role.role_id] || Layers;
          return (
            <div key={role.role_id} className="track-card">
              <div className="track-card-header">
                <div className="track-icon-box">
                  <IconComponent size={20} />
                </div>
                <span className="track-badge">Multi-Turn</span>
              </div>

              <h3 className="track-title">{role.title}</h3>
              <p className="track-description">{role.description}</p>

              <div className="track-skills-chips">
                {(role.default_skills || []).slice(0, 4).map((skill, i) => (
                  <span key={i} className="skill-chip">
                    {skill}
                  </span>
                ))}
                {role.default_skills?.length > 4 && (
                  <span className="skill-chip-more">+{role.default_skills.length - 4}</span>
                )}
              </div>

              <div className="track-footer">
                <button
                  className="btn btn-secondary track-action-btn"
                  onClick={() => onSelectPreset(role)}
                >
                  <span>Select & Calibrate</span>
                  <ArrowRight size={15} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default TrackPresetsGrid;
