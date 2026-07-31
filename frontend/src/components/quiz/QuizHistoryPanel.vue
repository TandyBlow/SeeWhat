<template>
  <div class="history-panel">
    <!-- Header tabs -->
    <div class="history-tabs">
      <button
        class="history-tab"
        :class="{ active: tab === 'node' }"
        @click="switchTab('node')"
      >
        本节点题库
      </button>
      <button
        class="history-tab"
        :class="{ active: tab === 'wrong' }"
        @click="switchTab('wrong')"
      >
        所有错题
      </button>
    </div>

    <!-- Loading -->
    <template v-if="isBusy">
      <div class="history-loading">加载中...</div>
    </template>

    <!-- Error -->
    <template v-else-if="errorMessage">
      <div class="history-error">{{ errorMessage }}</div>
      <button class="history-btn" @click="refresh">重试</button>
    </template>

    <!-- Quiz mode: showing a single question inline -->
    <template v-else-if="activeQuestion">
      <button class="history-back" @click="activeQuestion = null">
        ← 返回列表
      </button>

      <div class="history-quiz">
        <span class="quiz-type-badge">{{ activeQuestion.type_label }}</span>
        <div class="history-question-text">{{ activeQuestion.question }}</div>

        <!-- Single choice -->
        <div v-if="activeQuestion.question_type === 'single_choice'" class="history-options">
          <GlassWrapper
            v-for="(option, idx) in activeQuestion.options"
            :key="idx"
            class="history-option"
            :class="quizOptionClasses(idx)"
            interactive
            @click="onQuizOptionClick(idx)"
          >
            <div class="history-option-content">
              <span class="quiz-option-label">{{ optionLabels[idx] }}</span>
              <span class="quiz-option-text">{{ option }}</span>
            </div>
          </GlassWrapper>
        </div>

        <!-- True/false -->
        <div v-else-if="activeQuestion.question_type === 'true_false'" class="quiz-tf-options">
          <GlassWrapper
            class="quiz-tf-option"
            :class="quizTfClasses(0)"
            interactive
            @click="onQuizOptionClick(0)"
          >
            <div class="quiz-tf-content">正确</div>
          </GlassWrapper>
          <GlassWrapper
            class="quiz-tf-option"
            :class="quizTfClasses(1)"
            interactive
            @click="onQuizOptionClick(1)"
          >
            <div class="quiz-tf-content">错误</div>
          </GlassWrapper>
        </div>

        <!-- Short answer -->
        <div v-else-if="activeQuestion.question_type === 'short_answer'" class="quiz-sa-area">
          <textarea
            v-model="quizShortAnswer"
            class="quiz-sa-input"
            placeholder="请输入你的答案..."
            :disabled="quizShowResult"
            rows="4"
          />
        </div>

        <template v-if="quizShowResult">
          <div class="quiz-result" :class="quizIsCorrect ? 'correct' : 'wrong'">
            {{ quizResultText }}
          </div>
          <div v-if="activeQuestion.explanation" class="quiz-explanation">
            {{ activeQuestion.explanation }}
          </div>
          <button class="history-btn" @click="activeQuestion = null">返回列表</button>
        </template>

        <button
          v-else
          class="history-btn"
          :disabled="!quizCanConfirm"
          @click="confirmQuizAnswer"
        >
          确认
        </button>
      </div>
    </template>

    <!-- List mode: question list -->
    <template v-else>
      <template v-if="tab === 'node' && !activeNode">
        <div class="history-empty">请先选择一个知识点</div>
      </template>

      <template v-else-if="tab === 'node' && nodeQuestions.length === 0">
        <div class="history-empty">该知识点暂无题目，前去出题生成吧</div>
      </template>

      <template v-else-if="tab === 'wrong' && wrongList.length === 0">
        <div class="history-empty">暂无错题，继续保持！</div>
      </template>

      <div v-else class="history-list">
        <GlassWrapper
          v-for="q in displayList"
          :key="q.id"
          class="history-item"
          interactive
          @click="openQuestion(q)"
        >
          <div class="history-item-content">
            <div class="history-item-header">
              <span class="quiz-type-badge">{{ q.type_label }}</span>
              <span
                v-if="tab === 'node' && hasResult(q)"
                class="history-status"
                :class="getResult(q).last_correct ? 'correct' : 'wrong'"
              >
                {{ getResult(q).last_correct ? '答对' : '答错' }}
              </span>
            </div>
            <div class="history-item-question">{{ q.question }}</div>
          </div>
        </GlassWrapper>
      </div>
    </template>

    <!-- Bottom actions -->
    <div class="history-footer">
      <button class="history-btn secondary" @click="goBack">返回</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import GlassWrapper from '../ui/GlassWrapper.vue';
import { useQuizPanel } from './QuizHistoryPanelLogic';

const {
  tab, activeNode, isBusy, errorMessage, nodeQuestions, wrongList, displayList,
  activeQuestion, quizShowResult, quizShortAnswer, quizIsCorrect, quizResultText,
  quizCanConfirm, optionLabels, hasResult, getResult, quizOptionClasses,
  quizTfClasses, onQuizOptionClick, openQuestion, confirmQuizAnswer, switchTab,
  refresh, goBack,
} = useQuizPanel();
</script>

<style scoped src="./QuizHistoryPanel.1.css"></style>
<style scoped src="./QuizHistoryPanel.2.css"></style>
