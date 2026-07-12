/**
 * Mock data for development and demonstration
 */

import { EvidencePanel as EvidencePanelType } from './types';

const mockPapers = {
  transformers: {
    id: 'paper1',
    title: 'Attention Is All You Need',
    authors: ['Vaswani, A.', 'Shazeer, N.', 'Parmar, N.'],
    abstract: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...',
    year: 2017,
    citations: 85000,
    source: 'scholar' as const,
    doi: '10.5555/3295222.3295349',
    url: 'https://arxiv.org/abs/1706.03762',
    relevanceScore: 98,
  },
  bert: {
    id: 'paper2',
    title: 'BERT: Pre-training of Deep Bidirectional Transformers',
    authors: ['Devlin, J.', 'Chang, M.', 'Lee, K.'],
    abstract: 'We introduce BERT, a new method of pre-training language representations...',
    year: 2018,
    citations: 65000,
    source: 'scholar' as const,
    doi: '10.48550/arXiv.1810.04805',
    url: 'https://arxiv.org/abs/1810.04805',
    relevanceScore: 96,
  },
  gpt: {
    id: 'paper3',
    title: 'Language Models are Unsupervised Multitask Learners',
    authors: ['Radford, A.', 'Wu, J.', 'Child, R.'],
    abstract: 'Natural language processing tasks are typically approached with supervised learning on task-specific datasets...',
    year: 2019,
    citations: 55000,
    source: 'arxiv' as const,
    relevanceScore: 94,
  },
  federated: {
    id: 'paper4',
    title: 'Communication-Efficient Learning of Deep Networks from Decentralized Data',
    authors: ['McMahan, B.', 'Moore, E.', 'Ramage, D.'],
    abstract: 'Modern mobile devices have orders of magnitude more computational power than devices...',
    year: 2017,
    citations: 15000,
    source: 'scholar' as const,
    relevanceScore: 92,
  },
};

const mockCitations = {
  bert: {
    id: 'cite1',
    paperId: 'paper2',
    format: 'apa' as const,
    text: 'Devlin, J., Chang, M., & Lee, K. (2018). BERT: Pre-training of deep bidirectional transformers for language understanding. arXiv preprint arXiv:1810.04805.',
  },
  gpt: {
    id: 'cite2',
    paperId: 'paper3',
    format: 'apa' as const,
    text: 'Radford, A., Wu, J., Child, R., ... (2019). Language models are unsupervised multitask learners. OpenAI blog, 1(8), 9.',
  },
};

export const mockEvidenceData = {
  literatureReviewEvidence: {
    sourcePapers: [
      mockPapers.transformers,
      mockPapers.bert,
      mockPapers.gpt,
    ],
    supportingEvidence: [
      'Transformer architectures have achieved state-of-the-art results across 47 major NLP benchmarks',
      'Citation frequency increased 340% for transformer-based papers in the last 5 years',
      'Major tech companies (Google, Facebook, OpenAI) have adopted transformers as their primary architecture',
      'Transformer models demonstrate superior performance in zero-shot and few-shot learning scenarios',
    ],
    confidenceScore: 94,
    agentReasoningSummary:
      'The analysis of 3,247 papers from 2017-2024 shows a clear and consistent trend toward transformer-based architectures in NLP. The convergence is supported by empirical results showing transformers outperforming RNNs and CNNs on standard benchmarks, widespread industry adoption, and the mathematical elegance of the attention mechanism. The confidence score reflects the overwhelming consensus in the literature.',
    relatedCitations: [
      mockCitations.bert,
      mockCitations.gpt,
    ],
  } as EvidencePanelType,

  federatedLearningEvidence: {
    sourcePapers: [
      mockPapers.federated,
      mockPapers.transformers,
    ],
    supportingEvidence: [
      'Federated learning reduces data transfer by 99.8% compared to centralized training',
      'Privacy compliance rate improved to 99.4% with federated approaches',
      'Real-world deployments show 15-30% computational overhead but acceptable for privacy-critical applications',
      '2,341 papers on federated learning published in the last 3 years alone',
    ],
    confidenceScore: 87,
    agentReasoningSummary:
      'Federated learning is gaining significant traction in privacy-sensitive domains like healthcare and finance. The evidence base shows clear advantages in data privacy and reduced bandwidth usage, though communication efficiency remains a practical challenge. The moderate confidence score reflects ongoing research into optimization techniques.',
    relatedCitations: [
      mockCitations.bert,
    ],
  } as EvidencePanelType,

  gapAnalysisEvidence: {
    sourcePapers: [
      mockPapers.transformers,
      mockPapers.federated,
    ],
    supportingEvidence: [
      'Only 12% of papers address efficient transformer fine-tuning for resource-constrained devices',
      'Communication efficiency in federated settings remains unsolved for large models',
      'No standardized evaluation metrics for privacy-utility tradeoffs',
      'Interpretability of transformer attention mechanisms is still largely unexplored',
    ],
    confidenceScore: 81,
    agentReasoningSummary:
      'The identified gaps represent key research opportunities at the intersection of efficiency, privacy, and interpretability. These areas have received less attention in the literature (12-18% of papers) and represent both technical challenges and opportunities for significant impact.',
    relatedCitations: [],
  } as EvidencePanelType,

  novelDirectionsEvidence: {
    sourcePapers: [
      mockPapers.transformers,
      mockPapers.bert,
      mockPapers.federated,
    ],
    supportingEvidence: [
      'Emerging research shows promise in hybrid architectures combining transformers with sparse computation',
      'Differential privacy techniques when combined with federated learning show 3-5x efficiency improvements',
      'Transfer learning from large models to edge devices is an active area with growing interest',
      'Cross-domain federated learning shows potential for knowledge sharing while maintaining privacy',
    ],
    confidenceScore: 76,
    agentReasoningSummary:
      'Novel research directions combine multiple established techniques (transformers, federated learning, privacy preservation) in new ways. The evidence shows emerging momentum in these intersection areas, with 234 papers published in the last year alone. Lower confidence reflects the early-stage nature of these combined approaches.',
    relatedCitations: [
      mockCitations.bert,
      mockCitations.gpt,
    ],
  } as EvidencePanelType,
};
