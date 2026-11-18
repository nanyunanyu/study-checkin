<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Review } from '../types'
import { PROBLEM_OPTIONS } from '../utils'
import Icon from './Icon.vue'

const props = defineProps<{ review: Review; readonly?: boolean }>()
const emit = defineEmits<{ (event: 'update', patch: Partial<Review>): void }>()
const customProblem = ref('')
const visiblePriorityCount = computed(() => Math.max(3, props.review.priorities?.length || 0))
const customProblems = computed(() => (props.review.problems || []).filter((problem) => !PROBLEM_OPTIONS.includes(problem)))

function setBest(index: number, value: string) {
  const best = [...(props.review.best || ['', ''])]
  best[index] = value
  emit('update', { best })
}

function setPriority(index: number, value: string) {
  const priorities = [...(props.review.priorities || [])]
  while (priorities.length <= index) priorities.push('')
  priorities[index] = value
  emit('update', { priorities })
}

function addPriority() {
  emit('update', { priorities: [...(props.review.priorities || ['', '', '']), ''] })
}

function removePriority(index: number) {
  const priorities = [...(props.review.priorities || ['', '', ''])]
  priorities.splice(index, 1)
  while (priorities.length < 3) priorities.push('')
  emit('update', { priorities })
}

function toggleProblem(problem: string) {
  const set = new Set(props.review.problems || [])
  if (set.has(problem)) set.delete(problem)
  else set.add(problem)
  emit('update', { problems: [...set] })
}

function addCustomProblem() {
  const value = customProblem.value.trim()
  if (!value || (props.review.problems || []).includes(value)) return
  emit('update', { problems: [...(props.review.problems || []), value] })
  customProblem.value = ''
}

function removeCustomProblem(problem: string) {
  emit('update', { problems: (props.review.problems || []).filter((item) => item !== problem) })
}
</script>

<template>
  <section class="card">
    <div class="card-pad">
      <div class="card-head">
        <div class="card-title">今日复盘</div>
        <span v-if="readonly" class="tag">只读</span>
        <div class="spacer" />
        <span class="hint">每天留 3 分钟，写清楚问题比多刷一套题有用</span>
      </div>

      <div class="stack" style="gap: 14px">
        <div>
          <div class="hint" style="margin-bottom: 6px">最有效的学习内容</div>
          <div class="grid-2">
            <el-input
              :readonly="readonly"
              :value="review.best?.[0] || ''"
              placeholder="① 例如：晨背 40 分钟记了 60 个单词"
              @input="setBest(0, $event)"
            />
            <el-input
              :readonly="readonly"
              :value="review.best?.[1] || ''"
              placeholder="② 可留空"
              @input="setBest(1, $event)"
            />
          </div>
        </div>

        <div>
          <div class="hint" style="margin-bottom: 6px">今日问题</div>
          <div class="row review-problem-options">
            <el-button
              v-for="option in PROBLEM_OPTIONS"
              :key="option"
              class="chip-pick"
              :class="{ active: (review.problems || []).includes(option) }"
              :type="(review.problems || []).includes(option) ? 'primary' : 'default'"
              size="small"
              :disabled="readonly"
              @click="toggleProblem(option)"
            >
              {{ option }}
            </el-button>
          </div>
          <div v-if="customProblems.length" class="row review-custom-problems">
            <span v-for="problem in customProblems" :key="problem" class="custom-problem-tag">
              {{ problem }}
              <el-button v-if="!readonly" text circle type="danger" :aria-label="`删除问题：${problem}`" @click="removeCustomProblem(problem)">×</el-button>
            </span>
          </div>
          <form v-if="!readonly" class="review-custom-entry" @submit.prevent="addCustomProblem">
            <el-input v-model="customProblem" placeholder="输入自定义问题" maxlength="80" />
            <el-button type="primary" native-type="submit" :disabled="!customProblem.trim()"><Icon name="plus" :size="14" />添加问题</el-button>
          </form>
          <el-input
            v-if="(review.problems || []).includes('其他')"
            :readonly="readonly"
            :value="review.other"
            placeholder="具体是什么问题"
            style="margin-top: 8px"
            @input="emit('update', { other: $event })"
          />
        </div>

        <div>
          <div class="hint" style="margin-bottom: 6px">明日优先解决</div>
          <div class="stack" style="gap: 8px">
            <div v-for="index in visiblePriorityCount" :key="index" class="priority-row">
              <span class="priority-index">{{ index }}.</span>
              <el-input
                :readonly="readonly"
                :value="review.priorities?.[index - 1] || ''"
                :placeholder="`优先解决事项 ${index}`"
                @input="setPriority(index - 1, $event)"
              />
              <el-button v-if="!readonly && visiblePriorityCount > 3" class="priority-remove" text circle type="danger" :aria-label="`删除第 ${index} 项`" @click="removePriority(index - 1)"><Icon name="trash" :size="14" /></el-button>
            </div>
          </div>
          <el-button v-if="!readonly" class="add-priority-btn" type="primary" plain @click="addPriority"><Icon name="plus" :size="14" />新增优先事项</el-button>
        </div>

        <div>
          <div class="hint" style="margin-bottom: 6px">明日调整</div>
          <el-input
            type="textarea"
            :rows="3"
            :readonly="readonly"
            :value="review.adjustment"
            placeholder="例如：上午网课容易走神，改成先看 15 分钟再做笔记"
            @input="emit('update', { adjustment: $event })"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.review-problem-options,
.review-custom-problems {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.review-custom-problems {
  margin-top: 8px;
}

.custom-problem-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 32px;
  padding: 4px 8px 4px 11px;
  border: 1px solid var(--accent);
  border-radius: 99px;
  background: var(--accent-soft);
  color: var(--accent-text);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.custom-problem-tag button {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: inherit;
  font-size: 18px;
  line-height: 1;
}

.review-custom-entry {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.priority-row {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) 34px;
  align-items: center;
  gap: 6px;
}

.priority-index {
  color: var(--text-3);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.add-priority-btn {
  align-self: flex-start;
}

@media (max-width: 560px) {
  .review-custom-entry {
    flex-direction: column;
  }

  .review-custom-entry .btn {
    min-height: 42px;
  }
}
</style>
