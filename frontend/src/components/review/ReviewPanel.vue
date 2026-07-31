<template>
  <div class="review-panel">
    <template v-if="isBusy">
      <div class="review-loading">加载中...</div>
    </template>

    <template v-else-if="errorMessage">
      <div class="review-error">{{ errorMessage }}</div>
      <button class="review-btn" @click="goBack">返回</button>
    </template>

    <!-- Stats bar -->
    <template v-else-if="!allDone">
      <div class="review-stats-bar">
        <div class="review-stat">
          <span class="review-stat-value">{{ reviewedCount }}</span>
          <span class="review-stat-label">已复习</span>
        </div>
        <div class="review-stat">
          <span class="review-stat-value">{{ totalCount }}</span>
          <span class="review-stat-label">待复习</span>
        </div>
      </div>

      <!-- Current card -->
      <div v-if="currentItem" class="review-card">
        <div class="review-card-header">
          <span class="review-card-index">第 {{ reviewedCount + 1 }}/{{ totalCount }} 张卡片</span>
          <span v-if="currentItem.review_state === 'new'" class="review-tag review-tag-new">新</span>
          <span v-else-if="currentItem.review_state === 'relearning'" class="review-tag review-tag-relearn">重学</span>
          <span v-else class="review-tag review-tag-review">复习</span>
        </div>

        <h3 class="review-node-name">{{ currentItem.node_name }}</h3>

        <div class="review-meta">
          <span v-if="currentItem.retrievability > 0">
            记忆度 {{ Math.round(currentItem.retrievability * 100) }}%
          </span>
          <span v-else>首次复习</span>
        </div>

        <Transition name="content-expand">
          <div v-if="showContent" class="review-content">
            <div v-if="currentItem.content" class="review-content-text">
              {{ currentItem.content }}
            </div>
            <div v-else class="review-content-empty">暂无笔记内容</div>
          </div>
        </Transition>

        <button
          v-if="!showContent"
          class="review-btn review-btn-show"
          @click="showContent = true"
        >
          显示内容（回忆后点击核对）
        </button>

        <div v-else class="review-rating-group">
          <button class="review-rating rating-again" @click="rate(1)">忘了</button>
          <button class="review-rating rating-hard" @click="rate(2)">困难</button>
          <button class="review-rating rating-good" @click="rate(3)">正常</button>
          <button class="review-rating rating-easy" @click="rate(4)">轻松</button>
        </div>
      </div>

      <button class="review-btn review-btn-back" @click="goBack">返回</button>
    </template>

    <!-- All done -->
    <template v-else>
      <div class="review-done">
        <div class="review-done-icon">✅</div>
        <h2 class="review-done-title">今日复习完成</h2>
        <p class="review-done-sub">共复习 {{ reviewedCount }} 个知识点</p>
        <button class="review-btn" @click="goBack">返回</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useNodeStore } from '../../stores/nodeStore';
import { useReview, type DueReviewItem } from '../../composables/useReview';

const nodeStore = useNodeStore();
const { isBusy, errorMessage, fetchDueReviews, submitReview } = useReview();

const items = ref<DueReviewItem[]>([]);
const currentIndex = ref(0);
const showContent = ref(false);
const reviewedCount = ref(0);
const allDone = ref(false);

const totalCount = computed(() => items.value.length);
const currentItem = computed(() => items.value[currentIndex.value] ?? null);

onMounted(async () => {
  items.value = await fetchDueReviews(20);
  if (items.value.length === 0) {
    allDone.value = true;
  }
});

async function rate(rating: number): Promise<void> {
  const item = currentItem.value;
  if (!item) return;

  const result = await submitReview(item.node_id, rating);
  if (!result) return;

  reviewedCount.value++;
  showContent.value = false;

  if (currentIndex.value < items.value.length - 1) {
    currentIndex.value++;
  } else {
    allDone.value = true;
  }
}

function goBack(): void {
  nodeStore.cancelOperation();
}
</script>

<style scoped src="./ReviewPanel.1.css"></style>

<style scoped src="./ReviewPanel.2.css"></style>
