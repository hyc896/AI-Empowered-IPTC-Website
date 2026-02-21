<template>
  <div class="mindmap-page">
    <div class="mindmap-header">
      <button class="back-btn" @click="router.push('/graph')">← 返回</button>
      <span class="book-title">{{ bookTitle }}</span>
      <span class="hint">点击章节/小节/部可展开折叠，点击知识点查看详情</span>
    </div>
    <div class="mindmap-body">
      <div ref="container" class="mindmap-container"></div>
      <!-- 知识点详情面板 -->
      <div v-if="selectedKP" class="kp-panel">
        <div class="kp-panel-header">
          <span class="kp-name">{{ selectedKP.name }}</span>
          <button class="close-btn" @click="selectedKP = null">✕</button>
        </div>
        <div class="kp-panel-body">
          <div v-if="selectedKP.theory" class="kp-section">
            <div class="kp-section-title">理论描述</div>
            <div class="kp-section-content">{{ selectedKP.theory }}</div>
          </div>
          <div v-if="selectedKP.application" class="kp-section">
            <div class="kp-section-title">应用场景</div>
            <div class="kp-section-content">{{ selectedKP.application }}</div>
          </div>
          <div v-if="selectedKP.keywords" class="kp-section">
            <div class="kp-section-title">典型关键词</div>
            <div class="kp-keywords">
              <span v-for="kw in selectedKP.keywords.split(',')" :key="kw" class="kw-tag">{{ kw.trim() }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import * as d3 from 'd3';
import mindmapData from '@/data/mindmapData.json';

const route = useRoute();
const router = useRouter();
const container = ref<HTMLElement | null>(null);
const selectedKP = ref<{ name: string; theory: string; application: string; keywords: string } | null>(null);

const bookId = computed(() => route.params.bookId as string);
const bookData = computed(() => (mindmapData as any[]).find(b => b.id === bookId.value));
const bookTitle = computed(() => bookData.value?.name ?? '');

onMounted(() => {
  if (bookData.value && container.value) drawTree(container.value, bookData.value);
});

function buildHierarchy(book: any) {
  return {
    name: book.name, type: 'book',
    children: book.chapters.map((ch: any) => ({
      name: ch.name, type: 'chapter',
      children: ch.sections.map((sec: any) => ({
        name: sec.name, type: 'section',
        children: sec.parts.map((p: any) => ({
          name: p.name || '知识点', type: 'part',
          children: p.kps.map((kp: any) => ({ ...kp, type: 'kp' })),
        })),
      })),
    })),
  };
}

const COLORS: Record<string, string> = {
  book: '#ff6b6b', chapter: '#74b9ff', section: '#55efc4', part: '#fdcb6e', kp: '#ffeaa7',
};

function diagonal(s: any, d: any) {
  return `M${s.y},${s.x}C${(s.y + d.y) / 2},${s.x} ${(s.y + d.y) / 2},${d.x} ${d.y},${d.x}`;
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n) + '…' : s;
}

function drawTree(el: HTMLElement, book: any) {
  const W = el.clientWidth || 1200;
  const H = el.clientHeight || 700;
  const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
  const g = svg.append('g');

  const zoom = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.1, 3])
    .on('zoom', (e) => g.attr('transform', e.transform));
  svg.call(zoom as any);

  const root = d3.hierarchy(buildHierarchy(book)) as any;
  // 默认折叠 section 及以下层级，只展示章节
  root.descendants().forEach((d: any) => {
    if (d.depth >= 2 && d.children) {
      d._children = d.children;
      d.children = null;
    }
  });
  root.x0 = H / 2; root.y0 = 0;
  let uid = 0;

  function update(src: any) {
    d3.tree<any>().nodeSize([28, 240])(root);
    const nodes = root.descendants();
    const links = root.links();

    const link = g.selectAll<SVGPathElement, any>('path.link').data(links, (d: any) => d.target.id);
    link.enter().insert('path', 'g').attr('class', 'link')
      .attr('fill', 'none').attr('stroke', 'rgba(255,255,255,0.25)').attr('stroke-width', 1.5)
      .attr('d', () => diagonal({ x: src.x0, y: src.y0 }, { x: src.x0, y: src.y0 }))
      .merge(link as any).transition().duration(300)
      .attr('d', (d: any) => diagonal(d.source, d.target));
    link.exit().transition().duration(300)
      .attr('d', () => diagonal({ x: src.x, y: src.y }, { x: src.x, y: src.y })).remove();

    const node = g.selectAll<SVGGElement, any>('g.node').data(nodes, (d: any) => d.id || (d.id = ++uid));
    const enter = node.enter().append('g').attr('class', 'node')
      .attr('transform', () => `translate(${src.y0},${src.x0})`)
      .style('cursor', (d: any) => d.data.type === 'kp' ? 'pointer' : 'pointer')
      .on('click', (_: any, d: any) => {
        if (d.data.type === 'kp') {
          selectedKP.value = { name: d.data.name, theory: d.data.theory, application: d.data.application, keywords: d.data.keywords };
          return;
        }
        if (d.children) { d._children = d.children; d.children = null; }
        else { d.children = d._children; d._children = null; }
        update(d);
      });

    enter.append('circle').attr('r', 5);
    enter.append('text').attr('dy', '0.35em').style('font-family', 'sans-serif').style('user-select', 'none');
    enter.append('title');

    const merged = enter.merge(node as any);
    merged.transition().duration(300).attr('transform', (d: any) => `translate(${d.y},${d.x})`);

    merged.select('circle')
      .attr('r', (d: any) => d.data.type === 'book' ? 8 : 5)
      .attr('fill', (d: any) => d._children ? COLORS[d.data.type] : 'rgba(255,255,255,0.15)')
      .attr('stroke', (d: any) => COLORS[d.data.type] ?? '#fff')
      .attr('stroke-width', 2);

    merged.select('text')
      .attr('x', (d: any) => (d.children || d._children) ? -10 : 10)
      .attr('text-anchor', (d: any) => (d.children || d._children) ? 'end' : 'start')
      .style('font-size', (d: any) => d.data.type === 'kp' ? '11px' : '12px')
      .style('fill', (d: any) => COLORS[d.data.type] ?? '#fff')
      .style('text-shadow', '0 1px 3px rgba(0,0,0,0.8)')
      .text((d: any) => truncate(d.data.name, d.data.type === 'kp' ? 14 : 18));

    merged.select('title').text((d: any) => d.data.name);

    node.exit().transition().duration(300)
      .attr('transform', () => `translate(${src.y},${src.x})`).style('opacity', 0).remove();

    nodes.forEach((d: any) => { d.x0 = d.x; d.y0 = d.y; });
  }

  update(root);

  setTimeout(() => {
    const b = (g.node() as SVGGElement).getBBox();
    if (!b.width) return;
    const scale = Math.min(0.85, Math.min(W / (b.width + 80), H / (b.height + 60)));
    const tx = W / 2 - scale * (b.x + b.width / 2);
    const ty = H / 2 - scale * (b.y + b.height / 2);
    svg.call((zoom as any).transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
  }, 100);
}
</script>

<style scoped>
.mindmap-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--header-height));
}

.mindmap-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 24px;
  background: rgba(0,0,0,0.4);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(255,255,255,0.15);
  flex-shrink: 0;
}

.back-btn {
  padding: 6px 16px;
  border: 1px solid rgba(255,255,255,0.4);
  border-radius: 6px;
  background: rgba(255,255,255,0.1);
  color: #fff;
  cursor: pointer;
  font-size: var(--font-size-sm);
  transition: background 0.2s;
}
.back-btn:hover { background: rgba(255,255,255,0.2); }

.book-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: #fff;
}

.hint {
  font-size: var(--font-size-xs);
  color: rgba(255,255,255,0.6);
  margin-left: auto;
}

.mindmap-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.mindmap-container {
  flex: 1;
  overflow: hidden;
}

.kp-panel {
  width: 360px;
  background: rgba(0,0,0,0.75);
  backdrop-filter: blur(12px);
  border-left: 1px solid rgba(255,255,255,0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.kp-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.15);
  flex-shrink: 0;
}

.kp-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: #ffeaa7;
  line-height: 1.4;
}

.close-btn {
  background: none;
  border: none;
  color: rgba(255,255,255,0.6);
  cursor: pointer;
  font-size: 16px;
  padding: 4px;
  flex-shrink: 0;
}
.close-btn:hover { color: #fff; }

.kp-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.kp-section-title {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.kp-section-content {
  font-size: var(--font-size-sm);
  color: rgba(255,255,255,0.85);
  line-height: 1.7;
}

.kp-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.kw-tag {
  padding: 3px 10px;
  background: rgba(255,234,167,0.15);
  border: 1px solid rgba(255,234,167,0.3);
  border-radius: 20px;
  font-size: 12px;
  color: #ffeaa7;
}
</style>
