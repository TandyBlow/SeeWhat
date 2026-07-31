<template>
  <div class="quiz-panel">
    <template v-if="!activeNode">
      <div class="quiz-no-node">请先选择一个知识点再出题</div>
      <button class="quiz-btn" @click="goBack">返回</button>
    </template>

    <template v-else-if="isBusy">
      <div class="quiz-loading">出题中...</div>
    </template>

    <template v-else-if="errorMessage">
      <div class="quiz-error">{{ errorMessage }}</div>
      <div class="quiz-actions">
        <button class="quiz-btn" @click="retry">重试</button>
        <button class="quiz-btn secondary" @click="goBack">返回</button>
      </div>
    </template>

    <template v-else-if="currentQuestion">
      <!-- Question type label -->
      <div class="quiz-type-row">
        <span class="quiz-type-badge">{{ typeLabel }}</span>
        <span v-if="currentQuestion.difficulty" class="quiz-difficulty">{{ currentQuestion.difficulty }}</span>
      </div>

      <div class="quiz-question">{{ currentQuestion.question }}</div>

      <!-- Single choice options -->
      <div v-if="currentQuestion.question_type === 'single_choice'" class="quiz-options">
        <GlassWrapper
          v-for="(option, idx) in currentQuestion.options"
          :key="idx"
          class="quiz-option"
          :class="optionClasses(idx)"
          interactive
          @click="onOptionClick(idx)"
        >
          <div class="quiz-option-content">
            <span class="quiz-option-label">{{ optionLabels[idx] }}</span>
            <span class="quiz-option-text">{{ option }}</span>
          </div>
        </GlassWrapper>
      </div>

      <!-- True/False options -->
      <div v-else-if="currentQuestion.question_type === 'true_false'" class="quiz-tf-options">
        <GlassWrapper
          class="quiz-tf-option"
          :class="tfOptionClasses(0)"
          interactive
          @click="onOptionClick(0)"
        >
          <div class="quiz-tf-content">正确</div>
        </GlassWrapper>
        <GlassWrapper
          class="quiz-tf-option"
          :class="tfOptionClasses(1)"
          interactive
          @click="onOptionClick(1)"
        >
          <div class="quiz-tf-content">错误</div>
        </GlassWrapper>
      </div>

      <!-- Short answer input -->
      <div v-else-if="currentQuestion.question_type === 'short_answer'" class="quiz-sa-area">
        <textarea
          v-model="shortAnswerText"
          class="quiz-sa-input"
          placeholder="请输入你的答案..."
          :disabled="showResult"
          rows="4"
        />
      </div>

      <!-- Result feedback -->
      <template v-if="showResult">
        <div class="quiz-result" :class="isCorrect ? 'correct' : 'wrong'">
          {{ resultText }}
        </div>
        <div v-if="currentQuestion.explanation" class="quiz-explanation">
          {{ currentQuestion.explanation }}
        </div>
        <div class="quiz-actions">
          <button class="quiz-btn" @click="nextQuestion">下一题</button>
          <button class="quiz-btn secondary" @click="goBack">返回列表</button>
        </div>
      </template>

      <!-- Confirm button (not yet shown result) -->
      <button
        v-else
        class="quiz-btn"
        :disabled="!canConfirm"
        @click="confirmAndSubmit"
      >
        确认
      </button>
    </template>

    <!-- No question yet: show generate options -->
    <template v-else>
      <div class="quiz-generate">
        <h3 class="quiz-generate-title">出题</h3>
        <div class="quiz-type-options">
          <button
            v-for="qt in questionTypes"
            :key="qt.value"
            class="quiz-type-btn"
            :class="{ active: selectedType === qt.value }"
            @click="selectedType = qt.value"
          >
            {{ qt.label }}
          </button>
        </div>
        <button class="quiz-btn" @click="retry">生成题目</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import GlassWrapper from '../ui/GlassWrapper.vue';
import { useQuizPanel } from './useQuizPanel';

const {
  activeNode, isBusy, errorMessage, currentQuestion, showResult,
  shortAnswerText, selectedType, questionTypes, typeLabel, isCorrect,
  resultText, canConfirm, optionLabels, optionClasses, tfOptionClasses,
  onOptionClick, confirmAndSubmit, retry, nextQuestion, goBack,
} = useQuizPanel();
</script>

<style scoped src="./QuizPanel.1.css"></style>
<style scoped src="./QuizPanel.2.css"></style>
