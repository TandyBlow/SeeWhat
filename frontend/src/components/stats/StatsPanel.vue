<template>
  <div class="stats-panel">
    <template v-if="isBusy">
      <div class="stats-loading">加载中...</div>
    </template>

    <template v-else-if="errorMessage">
      <div class="stats-error">{{ errorMessage }}</div>
    </template>

    <template v-else>
      <!-- Growth stage header -->
      <div class="growth-stage">
        <span class="growth-stage-icon">{{ growthStage.icon }}</span>
        <span class="growth-stage-label">{{ growthStage.label }}</span>
      </div>

      <!-- Review progress bar -->
      <div class="coverage-section">
        <div class="coverage-header">
          <span class="coverage-label">复习覆盖</span>
          <span class="coverage-value">{{ Math.round(reviewCoverage * 100) }}%</span>
        </div>
        <div class="coverage-bar-track">
          <div
            class="coverage-bar-fill"
            :style="{ width: Math.round(reviewCoverage * 100) + '%' }"
          />
        </div>
      </div>

      <!-- Core stats -->
      <div class="stats-overview">
        <div class="stats-card">
          <div class="stats-value">{{ totalNodes }}</div>
          <div class="stats-label">知识点总数</div>
        </div>
        <div class="stats-card">
          <div class="stats-value">{{ Math.round(avgMastery * 100) }}%</div>
          <div class="stats-label">平均掌握度</div>
        </div>
        <div class="stats-card">
          <div class="stats-value">{{ quizzedCount }}</div>
          <div class="stats-label">已测验</div>
        </div>
      </div>

      <!-- Review row -->
      <div v-if="reviewStats" class="stats-overview stats-review-row">
        <div class="stats-card">
          <div class="stats-value">{{ reviewStats.due_count }}</div>
          <div class="stats-label">待复习</div>
        </div>
        <div class="stats-card">
          <div class="stats-value">{{ reviewStats.today_reviewed }}</div>
          <div class="stats-label">今日已复习</div>
        </div>
        <div class="stats-card">
          <div class="stats-value">{{ avgStabilityDays }}天</div>
          <div class="stats-label">平均稳定性</div>
        </div>
      </div>
      <div v-if="reviewErrorMessage && !reviewStats" class="stats-error">{{ reviewErrorMessage }}</div>

      <!-- Weak nodes -->
      <div v-if="weakNodes.length > 0" class="stats-section">
        <h3 class="stats-section-title">薄弱知识点</h3>
        <div class="stats-weak-list">
          <GlassWrapper
            v-for="node in weakNodes"
            :key="node.id"
            class="stats-weak-item"
          >
            <div class="stats-weak-content">
              <div class="stats-weak-left">
                <span class="stats-weak-name">{{ node.name }}</span>
                <span class="stats-weak-meta">
                  {{ node.review_count }}次复习 · 稳定性{{ formatStability(node.stability) }}
                </span>
              </div>
              <span class="stats-weak-score">{{ Math.round(node.mastery_score * 100) }}%</span>
            </div>
          </GlassWrapper>
        </div>
      </div>

      <button class="stats-btn" @click="goBack">返回</button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';

import GlassWrapper from '../ui/GlassWrapper.vue';
import { useNodeStore } from '../../stores/nodeStore';
import { useStats } from '../../composables/useStats';
import { useReview } from '../../composables/useReview';

const nodeStore = useNodeStore();

const { isBusy, errorMessage, nodes, fetchStats } = useStats();
const { reviewStats, fetchReviewStats, errorMessage: reviewErrorMessage } = useReview();

const totalNodes = computed(() => nodes.value.length);

const quizzedCount = computed(() =>
  nodes.value.filter(n => n.review_count > 0).length,
);

const reviewCoverage = computed(() =>
  totalNodes.value > 0 ? quizzedCount.value / totalNodes.value : 0,
);

const avgMastery = computed(() => {
  const quizzed = nodes.value.filter(n => n.review_count > 0);
  if (quizzed.length === 0) return 0;
  const sum = quizzed.reduce((acc, n) => acc + n.mastery_score, 0);
  return sum / quizzed.length;
});

const avgStabilityDays = computed(() => {
  const reviewed = nodes.value.filter(n => n.stability > 0);
  if (reviewed.length === 0) return 0;
  const sum = reviewed.reduce((acc, n) => acc + n.stability, 0);
  return Math.round(sum / reviewed.length * 10) / 10;
});

interface GrowthStageInfo {
  icon: string;
  label: string;
}

const growthStage = computed<GrowthStageInfo>(() => {
  const coverage = reviewCoverage.value;
  const stability = avgStabilityDays.value;
  if (coverage === 0) return { icon: '🌱', label: '种子阶段 · 开始学习吧' };
  if (coverage < 0.3 || stability < 2) return { icon: '🪴', label: '萌芽阶段 · 持续积累' };
  if (coverage < 0.6 || stability < 5) return { icon: '🌿', label: '生长阶段 · 稳步推进' };
  if (coverage < 0.9 || stability < 15) return { icon: '🌳', label: '繁茂阶段 · 知识扎根' };
  return { icon: '🏆', label: '参天大树 · 学识深厚' };
});

const weakNodes = computed(() =>
  [...nodes.value]
    .filter(n => n.review_count > 0 && n.mastery_score < 1)
    .sort((a, b) => a.mastery_score - b.mastery_score)
    .slice(0, 5),
);

function formatStability(s: number): string {
  if (s <= 0) return '未复习';
  if (s < 1) return `${Math.round(s * 24)}小时`;
  if (s < 30) return `${Math.round(s)}天`;
  return `${Math.round(s / 30)}月`;
}

function goBack(): void {
  nodeStore.cancelOperation();
}

onMounted(() => {
  fetchStats();
  fetchReviewStats();
});
</script>

<style scoped src="./StatsPanel.1.css"></style>
