<template>
  <n-space vertical :size="24">
    <n-grid :cols="4" :x-gap="16">
      <n-gi>
        <n-card>
          <n-statistic label="数据源总数" :value="stats.datasource_count" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card>
          <n-statistic label="今日查询数" :value="stats.query_count_today" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card>
          <n-statistic label="活跃用户" :value="stats.active_users" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card>
          <n-statistic label="错误率">
            <template #default>
              <n-text :type="stats.error_rate > 5 ? 'error' : 'success'">
                {{ stats.error_rate }}%
              </n-text>
            </template>
          </n-statistic>
        </n-card>
      </n-gi>
    </n-grid>
    <n-card title="查询趋势">
      <v-chart :option="chartOption" style="height: 350px" autoresize />
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent } from 'echarts/components'
import { getStats, getQueryTrend, type DashboardStats, type QueryTrend } from '@/api/dashboard'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, TitleComponent])

const stats = ref<DashboardStats>({
  datasource_count: 0,
  query_count_today: 0,
  active_users: 0,
  error_rate: 0,
})
const trend = ref<QueryTrend[]>([])

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: trend.value.map((t) => t.time) },
  yAxis: { type: 'value' },
  series: [{ type: 'line', data: trend.value.map((t) => t.count), smooth: true }],
}))

onMounted(async () => {
  try {
    stats.value = await getStats()
    trend.value = await getQueryTrend()
  } catch {
    // 接口未就绪时使用默认值
  }
})
</script>
