<template>
  <div class="daily-quiz-panel">
    <div class="activity-layout">
      <div class="activity-glass-host">
        <GlassWrapper>
          <div class="activity-scroll">
            <div class="quiz-inner">
              <DailyQuizPanelState
                v-if="queue.length === 0 || sessionFinished"
                :is-busy="isBusy"
                :queue-length="queue.length"
                :error-message="errorMessage"
                :session-finished="sessionFinished"
                :session-correct="sessionCorrect"
                @start="startSession"
                @back="goBack"
              />

              <!-- Active session -->
              <template v-else>
                <!-- Progress bar -->
                <div class="quiz-progress-row">
                  <span class="quiz-progress-text">{{ $t('official.sessionProgress', { current: progress.current, total: progress.total }) }}</span>
                  <div class="quiz-progress-track">
                    <div class="quiz-progress-fill" :style="{ width: progress.percent + '%' }"></div>
                  </div>
                  <button class="quiz-finish-btn" @click="finishSession">{{ $t('official.finishEarly') }}</button>
                </div>

                <!-- Node name -->
                <div class="quiz-node-name">{{ currentItem?.node_name ?? '' }}</div>

                <!-- Generating question -->
                <template v-if="isBusy && !currentQuestion">
                  <div class="quiz-state-center quiz-state-compact">
                    <div class="quiz-spinner quiz-spinner-sm"></div>
                    <div class="quiz-state-label">出题中...</div>
                  </div>
                </template>

                <!-- Question error (non-fatal) -->
                <template v-else-if="errorMessage && !currentQuestion">
                  <div class="quiz-error-card">
                    <div class="quiz-error-card-text">{{ errorMessage }}</div>
                    <div class="quiz-state-actions">
                      <button class="quiz-btn-ghost" @click="generateQuestion">重试</button>
                      <button class="quiz-btn-ghost" @click="skipQuestion">跳过</button>
                    </div>
                  </div>
                </template>

                <!-- Question active -->
                <template v-else-if="currentQuestion">
                  <!-- Type + difficulty row -->
                  <div class="quiz-meta-row">
                    <span class="quiz-type-badge">{{ typeLabel }}</span>
                    <span v-if="currentQuestion.difficulty" class="quiz-difficulty">{{ currentQuestion.difficulty }}</span>
                  </div>

                  <!-- Question text -->
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
                    <GlassWrapper inset class="quiz-sa-wrapper">
                      <textarea
                        v-model="shortAnswerText"
                        class="quiz-sa-input"
                        placeholder="请输入你的答案..."
                        :disabled="showResult"
                        rows="4"
                      />
                    </GlassWrapper>
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
                      <GlassWrapper class="quiz-btn-glass" interactive @click="advanceToNext">
                        <div class="quiz-btn-glass-label">{{ hasNext ? $t('official.nextQuestion') : '完成' }}</div>
                      </GlassWrapper>
                    </div>
                  </template>

                  <!-- Confirm button -->
                  <div v-else class="quiz-actions">
                    <GlassWrapper
                      class="quiz-btn-glass"
                      :class="{ 'quiz-btn-glass--disabled': !canConfirm }"
                      :interactive="canConfirm"
                      @click="canConfirm && confirmAndSubmit()"
                    >
                      <div class="quiz-btn-glass-label">确认</div>
                    </GlassWrapper>
                  </div>
                </template>

                <!-- No question generated yet -->
                <template v-else>
                  <div class="quiz-state-center quiz-state-compact">
                    <div class="quiz-spinner quiz-spinner-sm"></div>
                    <div class="quiz-state-label">准备为你出题...</div>
                  </div>
                </template>
              </template>
            </div>
          </div>
        </GlassWrapper>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import GlassWrapper from '../ui/GlassWrapper.vue'
import DailyQuizPanelState from './DailyQuizPanelState.vue'
import { useDailyQuizPanel } from './DailyQuizPanelLogic'

const {
  isBusy, errorMessage, currentQuestion, showResult, queue, sessionFinished, sessionCorrect,
  currentItem, progress, hasNext,
  typeLabel, isCorrect, resultText, canConfirm,
  optionLabels, shortAnswerText,
  optionClasses, tfOptionClasses,
  startSession, goBack, finishSession, generateQuestion, skipQuestion, onOptionClick,
  confirmAndSubmit, advanceToNext,
} = useDailyQuizPanel()
</script>

<style scoped src="./DailyQuizPanel.1.css"></style>
<style scoped src="./DailyQuizPanel.2.css"></style>
<style scoped src="./DailyQuizPanel.3.css"></style>
