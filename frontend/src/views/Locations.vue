<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const caps = ref<any[]>([])
const activeLoc = ref<number | null>(null)
const skuName = ref('')
const capVal = ref<number | null>(null)
const err = ref('')

async function loadCaps() {
  if (activeLoc.value == null) return
  caps.value = await api(`/locations/${activeLoc.value}/caps`)
}
async function saveCap() {
  err.value = ''
  const sku = skuName.value.trim()
  if (!sku) { err.value = '请填写商品名'; return }
  try {
    await api(`/locations/${activeLoc.value}/caps/${encodeURIComponent(sku)}`, {
      method: 'PUT',
      body: JSON.stringify({ cap: Number(capVal.value) }),
    })
    skuName.value = ''
    capVal.value = null
    await loadCaps()
  } catch {
    err.value = '登记被拒绝：合计补量上限必须为正整数（配置与单据保持改前）'
  }
}
async function removeCap(sku: string) {
  await api(`/locations/${activeLoc.value}/caps/${encodeURIComponent(sku)}`, { method: 'DELETE' })
  await loadCaps()
}
onMounted(async () => {
  rows.value = await api('/locations')
  if (rows.value.length) {
    activeLoc.value = rows.value[0].id
    await loadCaps()
  }
})
</script>
<template>
  <h1>点位 / 机位</h1>
  <p class="sub">左侧机位选择器对应的点位档案 · 同品合计补量上限在此维护</p>
  <div class="vf-site-rail" style="flex-direction:row;flex-wrap:wrap;border:none;background:transparent;padding:0;gap:0.5rem;margin-bottom:1rem">
    <div v-for="r in rows" :key="r.id ?? JSON.stringify(r)" class="vf-site-btn" style="min-width:140px">
      <strong style="display:block;color:var(--vf-led)">{{ r.code }}</strong>
      <span style="font-size:0.7rem">{{ r.name }}</span>
    </div>
  </div>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>地址</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)"><td>{{ r.code }}</td><td>{{ r.name }}</td><td>{{ r.address }}</td></tr>
      </tbody>
    </table>
  </div>
  <div class="card">
    <h2 style="margin:0 0 0.5rem;font-size:0.9rem">同品合计补量上限</h2>
    <p class="muted" style="margin:0 0 0.75rem;font-size:0.75rem">
      同一商品名的所有货道共享该上限：生成时按货道编号顺序累加，触顶后后续货道补量置 0（同品合计已满）。未登记的商品不受约束。
    </p>
    <div class="vf-form-row" style="margin-bottom:0.75rem">
      <label class="muted" style="font-size:0.78rem">点位</label>
      <select v-model.number="activeLoc" class="vf-select" @change="loadCaps">
        <option v-for="r in rows" :key="r.id" :value="r.id">{{ r.code }} · {{ r.name }}</option>
      </select>
    </div>
    <table v-if="caps.length">
      <thead><tr><th>商品名</th><th>合计补量上限</th><th></th></tr></thead>
      <tbody>
        <tr v-for="c in caps" :key="c.id">
          <td>{{ c.sku_name }}</td>
          <td><span class="badge badge-warn">{{ c.cap }}</span></td>
          <td><button class="btn btn-danger" @click="removeCap(c.sku_name)">删除</button></td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted" style="font-size:0.78rem">该点位尚未登记任何商品的合计上限。</p>
    <div class="vf-form-row" style="margin-top:0.75rem">
      <input v-model="skuName" class="vf-input" placeholder="商品名，如：薯片" />
      <input v-model.number="capVal" class="vf-input" type="number" min="1" placeholder="上限（正整数）" style="width:8.5rem" />
      <button class="btn" @click="saveCap">登记 / 更新</button>
    </div>
    <p v-if="err" class="vf-err">{{ err }}</p>
  </div>
</template>
