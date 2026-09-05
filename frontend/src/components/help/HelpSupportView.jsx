import React from 'react';
import { HelpCircle, Mic, Award, BookOpen, ShieldCheck, Play } from 'lucide-react';

/**
 * Dedicated Help & Support / Platform Guide View.
 * Provides clear explanations of evaluation dimensions, audio permissions, and interview mechanics.
 */
export function HelpSupportView({ onStartSetup }) {
  const faqs = [
    {
      q: 'How does AROVIA evaluate my interview responses?',
      a: 'AROVIA uses Google Gemini with structured output validation across 5 calibrated dimensions: Relevance (alignment with the question), Correctness (technical accuracy), Key Concepts (critical topic coverage), Clarity/Grammar (articulation and structural flow), and Confidence (pacing and tone).',
    },
    {
      q: 'How does speech recognition (STT) and voice synthesis (TTS) work?',
      a: 'AROVIA uses the browser Web Speech API. When the AI finishes asking a question, click the square microphone button to dictate your answer in real time. You can review and edit your transcribed answer in the live transcription box before submitting.',
    },
    {
      q: 'Can I practice with my own resume and specific Job Description?',
      a: 'Yes. In the Interview Setup screen, you can upload a PDF/DOCX resume and paste any Job Description. The AI will extract relevant context and tailor the scenario questions specifically to your background and the target role.',
    },
    {
      q: 'How can I download or save my performance evaluation report?',
      a: 'At the end of any interview session, AROVIA generates a multi-dimensional Performance Report Card with a 5-axis Radar chart. Click the "Download PDF" button to export a print-ready A4 evaluation summary.',
    },
  ];

  return (
    <div className="arovia-help-layout">
      {/* Header Banner */}
      <div className="help-header-banner">
        <div className="banner-text">
          <span className="banner-subtitle">GUIDANCE & DOCUMENTATION</span>
          <h1 className="banner-title">Help & Support</h1>
          <p className="banner-desc">
            Learn how the AROVIA adaptive AI interview system works, configure your audio environment,
            and understand your multi-dimensional performance metrics.
          </p>
        </div>

        <button className="start-assessment-cta-btn" onClick={onStartSetup}>
          <Play size={15} />
          <span>Launch Practice Session</span>
        </button>
      </div>

      {/* 3 Pillars Overview Grid */}
      <div className="help-pillars-grid">
        <div className="help-pillar-card">
          <div className="pillar-icon-box">
            <Award size={20} className="text-primary" />
          </div>
          <h3 className="pillar-title">5-Dimensional Model</h3>
          <p className="pillar-desc">
            Evaluates your answers across Relevance, Technical Correctness, Key Concepts,
            Clarity & Grammar, and Confidence Indicators.
          </p>
        </div>

        <div className="help-pillar-card">
          <div className="pillar-icon-box">
            <Mic size={20} className="text-cyan" />
          </div>
          <h3 className="pillar-title">Real-Time Voice Flow</h3>
          <p className="pillar-desc">
            Spoken AI questions combined with low-latency browser speech recognition
            and editable real-time transcripts.
          </p>
        </div>

        <div className="help-pillar-card">
          <div className="pillar-icon-box">
            <ShieldCheck size={20} className="text-success" />
          </div>
          <h3 className="pillar-title">Contextual Calibration</h3>
          <p className="pillar-desc">
            Ingests your real resume and target Job Description to simulate high-stakes,
            role-specific technical and behavioral interviews.
          </p>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="help-faq-section">
        <div className="faq-header-line">
          <BookOpen size={18} className="text-secondary" />
          <h3 className="section-title">Frequently Asked Questions</h3>
        </div>

        <div className="faq-items-list">
          {faqs.map((faq, idx) => (
            <div key={idx} className="faq-card-item">
              <h4 className="faq-question">{faq.q}</h4>
              <p className="faq-answer">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default HelpSupportView;
