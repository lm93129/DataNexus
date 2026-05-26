<template>
  <n-space vertical :size="24">
    <!-- 顶部统计卡片 -->
    <n-grid :cols="5" :x-gap="16">
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
      <n-gi>
        <n-card>
          <n-statistic label="待处理告警">
            <template #default>
              <n-text :type="pendingAlerts > 0 ? 'error' : 'success'">
                {{ pendingAlerts }}
              </n-text>
            </template>
          </n-statistic>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 时间范围选择 + 调用趋势 -->
    <n-card title="调用趋势">
      <template #header-extra>
        <n-radio-group v-model:value="trendRange" size="small" @update:value="loadTrend">
          <n-radio-button value="24h">24小时</n-radio-button>
          <n-radio-button value="7d">7天</n-radio-button>
          <n-radio-button value="30d">30天</n-radio-button>
        </n-radio-group>
      </template>
      <v-chart :option="trendChartOption" style="height: 300px" autoresize />
    </n-card>

    <!-- 多维度统计 -->
    <n-grid :cols="2" :x-gap="16">
      <n-gi>
        <n-card title="用户调用 Top 10">
          <v-chart :option="topUsersChartOption" style="height: 280px" autoresize />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="数据源调用 Top 10">
          <v-chart :option="topDsChartOption" style="height: 280px" autoresize />
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 错误率趋势 -->
    <n-card title="错误率趋势">
      <v-chart :option="errorChartOption" style="height: 280px" autoresize />
    </n-card>

    <!-- 慢查询排行 -->
    <n-card title="慢查询排行">
      <n-data-table :columns="slowColumns" :data="slowQueries" :max-height="300" />
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent, LegendComponent } from 'echarts/components'
import {
  getStats, getQueryTrend, getHourlyTrend, getTopUsers, getTopDatasources,
  getSlowQueries, getErrorStats,
  type DashboardStats, type QueryTrend, type TopUser, type TopDatasource, type SlowQuery, type ErrorStat,
} from '@/api/dashboard'
import { getPendingAlertCount } from '@/api/alert'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, TitleComponent, LegendComponent])

const stats = ref<DashboardStats>({ datasource_count: 0, query_count_today: 0, active_users: 0, error_rate: 0 })
const trend = ref<QueryTrend[]>([])
const topUsers = ref<TopUser[]>([])
const topDs = ref<TopDatasource[]>([])
const slowQueries = ref<SlowQuery[]>([])
const errorStats = ref<ErrorStat[]>([])
const trendRange = ref('7d')
const pendingAlerts = ref(0)

const trendChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: trend.value.map(t => t.time.replace('T', ' ').slice(5, 16)) },
  yAxis: { type: 'value' },
  series: [{ type: 'line', data: trend.value.map(t => t.count), smooth: true, areaStyle: { opacity: 0.15 } }],
}))

const topUsersChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: topUsers.value.map(u => u.username).reverse() },
  series: [{ type: 'bar', data: topUsers.value.map(u => u.count).reverse() }],
  grid: { left: 80 },
}))

const topDsChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: topDs.value.map(d => d.datasource.replace('datasource:', 'DS#')).reverse() },
  series: [{ type: 'bar', data: topDs.value.map(d => d.count).reverse() }],
  grid: { left: 80 },
}))

const errorChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['成功', '失败'] },
  xAxis: { type: 'category', data: errorStats.value.map(e => e.date.slice(5)) },
  yAxis: { type: 'value' },
  series: [
    { name: '成功', type: 'line', data: errorStats.value.map(e => e.success), smooth: true, itemStyle: { color: '#18a058' } },
    { name: '失败', type: 'line', data: errorStats.value.map(e => e.errors), smooth: true, itemStyle: { color: '#d03050' } },
  ],
}))

const slowColumns = [
  { title: 'SQL', key: 'sql', ellipsis: { tooltip: true }, width: 300 },
  { title: '耗时(ms)', key: 'duration_ms', width: 100, sorter: (a: SlowQuery, b: SlowQuery) => a.duration_ms - b.duration_ms },
  { title: '数据源', key: 'resource', width: 120 },
  { title: '状态', key: 'status', width: 80 },
  { title: '时间', key: 'created_at', width: 170, render: (row: SlowQuery) => row.created_at?.replace('T', ' ').slice(0, 19) },
]

async function loadTrend() {
  try {
    if (trendRange.value === '24h') {
      trend.value = await getHourlyTrend(24)
    } else {
      const days = trendRange.value === '7d' ? 7 : 30
      trend.value = await getQueryTrend(days)
    }
  } catch { /* ignore */ }
}

onMounted(async () => {
  try { stats.value = await getStats() } catch { /* ignore */ }
  await loadTrend()
  try { topUsers.value = await getTopUsers(7, 10) } catch { /* ignore */ }
  try { topDs.value = await getTopDatasources(7, 10) } catch { /* ignore */ }
  try { slowQueries.value = await getSlowQueries(7, 500) } catch { /* ignore */ }
  try { errorStats.value = await getErrorStats(7) } catch { /* ignore */ }
  try { const res = await getPendingAlertCount(); pendingAlerts.value = res.count } catch { /* ignore */ }
})
</script>
