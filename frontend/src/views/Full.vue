<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const lanes = ref<any[]>([])
onMounted(async () => {
  const ticket = await api('/refills/latest?location_id=1')
  const body = await api('/refills/full?location_id=1')
  // 以后端满仓页为准；只合并小票上 status=full 的行做兜底。
  // 同品合计触顶（sku_cap_full）、超占等零补量行不是单道满仓，不得并入。
  const extra = (ticket.lines || []).filter((l: any) => l.status === 'full')
  const map = new Map((body.lanes || []).map((l: any) => [l.lane_id, l]))
  for (const l of extra) map.set(l.lane_id, l)
  lanes.value = Array.from(map.values())
})
</script>
<template>
  <h1>满仓</h1>
  <p class="sub">缺口为 0 的货道（无需补货）</p>
  <div class="card">
    <table>
      <thead><tr><th>货道</th><th>商品</th><th>库存</th><th>在途</th><th>容量</th></tr></thead>
      <tbody>
        <tr v-for="l in lanes" :key="l.lane_id">
          <td>{{ l.slot_no }}</td><td>{{ l.sku_name }}</td><td>{{ l.stock }}</td><td>{{ l.in_transit }}</td><td>{{ l.capacity }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
