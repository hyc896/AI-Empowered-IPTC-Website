/**
 * 主应用组件
 * 对照 Cosma 原版布局：左侧菜单、中间图谱、右侧记录详情
 */

<template>
  <div class="app">
    <!-- 左侧菜单面板 -->
    <aside id="menu-container" class="menu active">
      <header>
        <div class="load-bar" title="GraphRAG Visualizer">
          <div class="load-bar-value"></div>
        </div>
        <button class="upload-btn" @click="triggerFileUpload" :disabled="uploading">
          <svg
            aria-hidden="true"
            stroke="currentColor"
            stroke-width="2"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              stroke-width="2"
              stroke="#ffffff"
              d="M13.5 3H12H8C6.34315 3 5 4.34315 5 6V18C5 19.6569 6.34315 21 8 21H11M13.5 3L19 8.625M13.5 3V7.625C13.5 8.17728 13.9477 8.625 14.5 8.625H19M19 8.625V11.8125"
              stroke-linejoin="round"
              stroke-linecap="round"
            ></path>
            <path
              stroke-linejoin="round"
              stroke-linecap="round"
              stroke-width="2"
              stroke="#ffffff"
              d="M17 15V18M17 21V18M17 18H14M17 18H20"
            ></path>
          </svg>
          {{ uploading ? '上传中...' : '上传文件' }}
        </button>
        <button class="settings-btn" @click="showSettingsDialog = true" title="LLM设置">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M19.4 15C19.2669 15.3016 19.2272 15.6362 19.286 15.9606C19.3448 16.285 19.4995 16.5843 19.73 16.82L19.79 16.88C19.976 17.0657 20.1235 17.2863 20.2241 17.5291C20.3248 17.7719 20.3766 18.0322 20.3766 18.295C20.3766 18.5578 20.3248 18.8181 20.2241 19.0609C20.1235 19.3037 19.976 19.5243 19.79 19.71C19.6043 19.896 19.3837 20.0435 19.1409 20.1441C18.8981 20.2448 18.6378 20.2966 18.375 20.2966C18.1122 20.2966 17.8519 20.2448 17.6091 20.1441C17.3663 20.0435 17.1457 19.896 16.96 19.71L16.9 19.65C16.6643 19.4195 16.365 19.2648 16.0406 19.206C15.7162 19.1472 15.3816 19.1869 15.08 19.32C14.7842 19.4468 14.532 19.6572 14.3543 19.9255C14.1766 20.1938 14.0813 20.5082 14.08 20.83V21C14.08 21.5304 13.8693 22.0391 13.4942 22.4142C13.1191 22.7893 12.6104 23 12.08 23C11.5496 23 11.0409 22.7893 10.6658 22.4142C10.2907 22.0391 10.08 21.5304 10.08 21V20.91C10.0723 20.579 9.96512 20.258 9.77251 19.9887C9.5799 19.7194 9.31074 19.5143 9 19.4C8.69838 19.2669 8.36381 19.2272 8.03941 19.286C7.71502 19.3448 7.41568 19.4995 7.18 19.73L7.12 19.79C6.93425 19.976 6.71368 20.1235 6.47088 20.2241C6.22808 20.3248 5.96783 20.3766 5.705 20.3766C5.44217 20.3766 5.18192 20.3248 4.93912 20.2241C4.69632 20.1235 4.47575 19.976 4.29 19.79C4.10405 19.6043 3.95653 19.3837 3.85588 19.1409C3.75523 18.8981 3.70343 18.6378 3.70343 18.375C3.70343 18.1122 3.75523 17.8519 3.85588 17.6091C3.95653 17.3663 4.10405 17.1457 4.29 16.96L4.35 16.9C4.58054 16.6643 4.73519 16.365 4.794 16.0406C4.85282 15.7162 4.81312 15.3816 4.68 15.08C4.55324 14.7842 4.34276 14.532 4.07447 14.3543C3.80618 14.1766 3.49179 14.0813 3.17 14.08H3C2.46957 14.08 1.96086 13.8693 1.58579 13.4942C1.21071 13.1191 1 12.6104 1 12.08C1 11.5496 1.21071 11.0409 1.58579 10.6658C1.96086 10.2907 2.46957 10.08 3 10.08H3.09C3.42099 10.0723 3.742 9.96512 4.0113 9.77251C4.28059 9.5799 4.48572 9.31074 4.6 9C4.73312 8.69838 4.77282 8.36381 4.714 8.03941C4.65519 7.71502 4.50054 7.41568 4.27 7.18L4.21 7.12C4.02405 6.93425 3.87653 6.71368 3.77588 6.47088C3.67523 6.22808 3.62343 5.96783 3.62343 5.705C3.62343 5.44217 3.67523 5.18192 3.77588 4.93912C3.87653 4.69632 4.02405 4.47575 4.21 4.29C4.39575 4.10405 4.61632 3.95653 4.85912 3.85588C5.10192 3.75523 5.36217 3.70343 5.625 3.70343C5.88783 3.70343 6.14808 3.75523 6.39088 3.85588C6.63368 3.95653 6.85425 4.10405 7.04 4.29L7.1 4.35C7.33568 4.58054 7.63502 4.73519 7.95941 4.794C8.28381 4.85282 8.61838 4.81312 8.92 4.68H9C9.29577 4.55324 9.54802 4.34276 9.72569 4.07447C9.90337 3.80618 9.99872 3.49179 10 3.17V3C10 2.46957 10.2107 1.96086 10.5858 1.58579C10.9609 1.21071 11.4696 1 12 1C12.5304 1 13.0391 1.21071 13.4142 1.58579C13.7893 1.96086 14 2.46957 14 3V3.09C14.0013 3.41179 14.0966 3.72618 14.2743 3.99447C14.452 4.26276 14.7042 4.47324 15 4.6C15.3016 4.73312 15.6362 4.77282 15.9606 4.714C16.285 4.65519 16.5843 4.50054 16.82 4.27L16.88 4.21C17.0657 4.02405 17.2863 3.87653 17.5291 3.77588C17.7719 3.67523 18.0322 3.62343 18.295 3.62343C18.5578 3.62343 18.8181 3.67523 19.0609 3.77588C19.3037 3.87653 19.5243 4.02405 19.71 4.21C19.896 4.39575 20.0435 4.61632 20.1441 4.85912C20.2448 5.10192 20.2966 5.36217 20.2966 5.625C20.2966 5.88783 20.2448 6.14808 20.1441 6.39088C20.0435 6.63368 19.896 6.85425 19.71 7.04L19.65 7.1C19.4195 7.33568 19.2648 7.63502 19.206 7.95941C19.1472 8.28381 19.1869 8.61838 19.32 8.92V9C19.4468 9.29577 19.6572 9.54802 19.9255 9.72569C20.1938 9.90337 20.5082 9.99872 20.83 10H21C21.5304 10 22.0391 10.2107 22.4142 10.5858C22.7893 10.9609 23 11.4696 23 12C23 12.5304 22.7893 13.0391 22.4142 13.4142C22.0391 13.7893 21.5304 14 21 14H20.91C20.5882 14.0013 20.2738 14.0966 20.0055 14.2743C19.7372 14.452 19.5268 14.7042 19.4 15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,.txt"
          style="display: none"
          @change="handleFileUpload"
        />
      </header>

      <!-- 进度条 -->
      <ProgressBar
        v-if="showProgress && uploadProgress"
        :visible="showProgress"
        :title="uploadProgress.message"
        :progress="uploadProgress.progress"
        :status="uploadProgress.status"
        :message="uploadProgress.message"
        :total-blocks="uploadProgress.total_blocks"
        :current-block="uploadProgress.current_block"
        :entities-count="uploadProgress.entities_count"
        :relations-count="uploadProgress.relations_count"
      />

      <!-- 文件列表 -->
      <details class="menu-index" open>
        <summary class="menu-title">
          <div class="title-left">
            <svg class="list-expand-icon" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
              <path d="M558.933333 490.666667L384 665.6l59.733333 59.733333 234.666667-234.666666L443.733333 256 384 315.733333l174.933333 174.933334z" fill="currentColor"></path>
            </svg>
            文件列表
          </div>
          <span class="badge">{{ files.length }}</span>
        </summary>

        <div v-if="loading" class="loading">加载中...</div>
        <ul v-else class="menu-index-list">
          <li
            v-for="file in files"
            :key="file.file_id"
            :class="{ active: selectedFileId === file.file_id }"
          >
            <a :href="`#${file.file_id}`" @click.prevent="handleFileSelect(file.file_id)">
              <span class="record-type-points">⬤</span>
              <span>{{ file.name || formatFileId(file.file_id) }}</span>
              <span class="badge">{{ file.entity_count }}</span>
            </a>
            <div class="file-actions">
              <button @click.stop="handleRename(file.file_id, file.name)" class="rename-btn">
                <svg class="edit-icon" viewBox="0 0 512 512">
                  <path d="M410.3 231l11.3-11.3-33.9-33.9-62.1-62.1L291.7 89.8l-11.3 11.3-22.6 22.6L58.6 322.9c-10.4 10.4-18 23.3-22.2 37.4L1 480.7c-2.5 8.4-.2 17.5 6.1 23.7s15.3 8.5 23.7 6.1l120.3-35.4c14.1-4.2 27-11.8 37.4-22.2L387.7 253.7 410.3 231zM160 399.4l-9.1 22.7c-4 3.1-8.5 5.4-13.3 6.9L59.4 452l23-78.1c1.4-4.9 3.8-9.4 6.9-13.3l22.7-9.1v32c0 8.8 7.2 16 16 16h32zM362.7 18.7L348.3 33.2 325.7 55.8 314.3 67.1l33.9 33.9 62.1 62.1 33.9 33.9 11.3-11.3 22.6-22.6 14.5-14.5c25-25 25-65.5 0-90.5L453.3 18.7c-25-25-65.5-25-90.5 0zm-47.4 168l-144 144c-6.2 6.2-16.4 6.2-22.6 0s-6.2-16.4 0-22.6l144-144c6.2-6.2 16.4-6.2 22.6 0s6.2 16.4 0 22.6z"></path>
                </svg>
                <span class="tooltip">重命名</span>
              </button>
              <button @click.stop="handleDelete(file.file_id)" class="delete-btn">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 50 59" class="bin">
                  <path fill="#B5BAC1" d="M0 7.5C0 5.01472 2.01472 3 4.5 3H45.5C47.9853 3 50 5.01472 50 7.5V7.5C50 8.32843 49.3284 9 48.5 9H1.5C0.671571 9 0 8.32843 0 7.5V7.5Z"></path>
                  <path fill="#B5BAC1" d="M17 3C17 1.34315 18.3431 0 20 0H29.3125C30.9694 0 32.3125 1.34315 32.3125 3V3H17V3Z"></path>
                  <path fill="#B5BAC1" d="M2.18565 18.0974C2.08466 15.821 3.903 13.9202 6.18172 13.9202H43.8189C46.0976 13.9202 47.916 15.821 47.815 18.0975L46.1699 55.1775C46.0751 57.3155 44.314 59.0002 42.1739 59.0002H7.8268C5.68661 59.0002 3.92559 57.3155 3.83073 55.1775L2.18565 18.0974ZM18.0003 49.5402C16.6196 49.5402 15.5003 48.4209 15.5003 47.0402V24.9602C15.5003 23.5795 16.6196 22.4602 18.0003 22.4602C19.381 22.4602 20.5003 23.5795 20.5003 24.9602V47.0402C20.5003 48.4209 19.381 49.5402 18.0003 49.5402ZM29.5003 47.0402C29.5003 48.4209 30.6196 49.5402 32.0003 49.5402C33.381 49.5402 34.5003 48.4209 34.5003 47.0402V24.9602C34.5003 23.5795 33.381 22.4602 32.0003 22.4602C30.6196 22.4602 29.5003 23.5795 29.5003 24.9602V47.0402Z" clip-rule="evenodd" fill-rule="evenodd"></path>
                  <path fill="#B5BAC1" d="M2 13H48L47.6742 21.28H2.32031L2 13Z"></path>
                </svg>
                <span class="tooltip">删除</span>
              </button>
            </div>
          </li>
        </ul>
      </details>
    </aside>

    <!-- 中间图谱区域 -->
    <div class="graph-wrapper">
      <div v-if="graphLoading" class="loading-overlay">
        <div class="spinner">加载图谱中...</div>
      </div>
      <CosmaViewer
        v-else-if="cosmaRecords.length > 0"
        :records="cosmaRecords"
        @node-click="handleNodeClick"
      />
      <div v-else class="empty-state">
        <p>请从左侧选择文件查看图谱</p>
      </div>
    </div>

    <!-- 右侧记录详情面板 -->
    <main id="record-container" class="record-container">
      <article v-if="!selectedRecord" class="record active empty-record">
        <p>点击图谱中的节点查看详情</p>
      </article>
      <article v-else class="record active">
        <header>
          <h1>{{ selectedRecord.title }}</h1>
          <div class="search-buttons">
            <button @click="handleSearchBaike" class="search-btn" :disabled="searching">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M21 21L15 15M17 10C17 13.866 13.866 17 10 17C6.13401 17 3 13.866 3 10C3 6.13401 6.13401 3 10 3C13.866 3 17 6.13401 17 10Z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              {{ searching ? '搜索中...' : '百科' }}
            </button>
            <button @click="handleSearchBooks" class="search-btn books-btn" :disabled="searchingBooks">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5A2.5 2.5 0 0 0 6.5 22H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              {{ searchingBooks ? '搜索中...' : '图书' }}
            </button>
            <button v-if="selectedRecord?.metas?.page_range" @click="handleOpenPDF" class="search-btn pdf-btn">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              打开PDF
            </button>
          </div>
        </header>
        <div class="record-content" v-html="renderedContent"></div>
        <div v-if="baikeResult" class="baike-result">
          <h3>百度百科</h3>
          <div v-if="baikeResult.success">
            <p class="baike-summary">{{ baikeResult.summary }}</p>
            <div v-if="baikeResult.info && Object.keys(baikeResult.info).length > 0" class="baike-info">
              <div v-for="(value, key) in baikeResult.info" :key="key" class="info-item">
                <strong>{{ key }}:</strong> {{ value }}
              </div>
            </div>
            <a :href="baikeResult.url" target="_blank" class="baike-link">查看完整词条 →</a>
          </div>
          <p v-else class="baike-error">{{ baikeResult.message }}</p>
        </div>
        <div v-if="booksResult" class="books-result">
          <h3>相关图书</h3>
          <div v-if="booksResult.success && booksResult.books">
            <div v-for="(book, index) in displayedBooks" :key="index" class="book-item">
              <img v-if="book.cover" :src="book.cover" :alt="book.title" class="book-cover" />
              <div class="book-info">
                <h4>{{ book.title }}</h4>
                <p v-if="book.author" class="book-author">作者：{{ book.author }}</p>
                <p v-if="book.publisher" class="book-publisher">出版社：{{ book.publisher }}</p>
                <p v-if="book.isbn" class="book-isbn">ISBN：{{ book.isbn }}</p>
                <p v-if="book.description" class="book-description">{{ book.description }}</p>
                <a v-if="book.link" :href="book.link" target="_blank" class="book-link">查看详情 →</a>
              </div>
            </div>
            <button
              v-if="booksResult.books.length > 3"
              @click="showAllBooks = !showAllBooks"
              class="expand-button"
            >
              {{ showAllBooks ? '收起' : `展开更多 (${booksResult.books.length - 3})` }}
            </button>
            <p v-if="booksResult.total && booksResult.total > booksResult.books.length" class="books-total">
              共找到 {{ booksResult.total }} 本相关图书，显示前 {{ booksResult.books.length }} 本
            </p>
          </div>
          <p v-else class="books-error">{{ booksResult.message }}</p>
        </div>
        <footer v-if="uniqueLinks.length > 0">
          <h3>关联链接 ({{ uniqueLinks.length }})</h3>
          <ul>
            <li v-for="link in uniqueLinks" :key="`${link.type}-${link.target_name}`">
              <strong>{{ translateType(link.type) }}</strong> → {{ link.target_name }}
            </li>
          </ul>
        </footer>
      </article>
    </main>

    <!-- 对话框组件 -->
    <ConfirmDialog
      ref="deleteDialog"
      title="确认删除"
      message="确定要删除此文件吗？此操作将删除 Neo4j 中的所有相关数据。"
      @confirm="confirmDelete"
    />

    <ConfirmDialog
      ref="uploadSuccessDialog"
      title="上传成功"
      message="文件上传成功！"
      :show-cancel="false"
    />

    <ConfirmDialog
      ref="uploadErrorDialog"
      title="上传失败"
      message="文件上传失败，请重试。"
      :show-cancel="false"
    />

    <InputDialog
      ref="renameDialog"
      title="重命名文件"
      message="请输入新的文件名称："
      placeholder="请输入新名称"
      @confirm="confirmRename"
    />

    <ConfirmDialog
      ref="renameSuccessDialog"
      title="重命名成功"
      message="文件重命名成功！"
      :show-cancel="false"
    />

    <ConfirmDialog
      ref="renameErrorDialog"
      title="重命名失败"
      message="文件重命名失败，请重试。"
      :show-cancel="false"
    />

    <ConfirmDialog
      ref="deleteSuccessDialog"
      title="删除成功"
      message="文件删除成功！"
      :show-cancel="false"
    />

    <ConfirmDialog
      ref="deleteErrorDialog"
      title="删除失败"
      message="文件删除失败，请重试。"
      :show-cancel="false"
    />

    <!-- LLM设置弹窗 -->
    <SettingsDialog
      :visible="showSettingsDialog"
      @close="showSettingsDialog = false"
      @saved="handleSettingsSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { marked } from 'marked';
import CosmaViewer from './components/CosmaViewer.vue';
import ConfirmDialog from './components/Dialog/ConfirmDialog.vue';
import InputDialog from './components/Dialog/InputDialog.vue';
import SettingsDialog from './components/Dialog/SettingsDialog.vue';
import { getFileList, getCosmaData, renameFile, deleteFile, searchBaike, searchBooks, getFileProgress, type BaikeResult, type BooksResult, type ProgressInfo } from './api/graph';
import { uploadFile } from './api/upload';
import type { FileInfo } from './api/graph';
import type { CosmaRecord } from './types/cosma';
import ProgressBar from './components/Progress/ProgressBar.vue';

const files = ref<FileInfo[]>([]);
const selectedFileId = ref('');
const cosmaRecords = ref<CosmaRecord[]>([]);
const selectedRecord = ref<CosmaRecord | null>(null);
const loading = ref(false);
const uploading = ref(false);
const graphLoading = ref(false);
const fileInput = ref<HTMLInputElement>();
const searching = ref(false);
const baikeResult = ref<BaikeResult | null>(null);
const searchingBooks = ref(false);
const booksResult = ref<BooksResult | null>(null);
const showAllBooks = ref(false);
const showSettingsDialog = ref(false);

// 进度相关
const uploadProgress = ref<ProgressInfo | null>(null);
const showProgress = ref(false);
let progressTimer: number | null = null;

// 对话框相关
const deleteDialog = ref<InstanceType<typeof ConfirmDialog>>();
const uploadSuccessDialog = ref<InstanceType<typeof ConfirmDialog>>();
const uploadErrorDialog = ref<InstanceType<typeof ConfirmDialog>>();
const renameDialog = ref<InstanceType<typeof InputDialog>>();
const renameSuccessDialog = ref<InstanceType<typeof ConfirmDialog>>();
const renameErrorDialog = ref<InstanceType<typeof ConfirmDialog>>();
const deleteSuccessDialog = ref<InstanceType<typeof ConfirmDialog>>();
const deleteErrorDialog = ref<InstanceType<typeof ConfirmDialog>>();
const pendingDeleteFileId = ref<string>('');
const pendingRenameFileId = ref<string>('');
const pendingRenameFileName = ref<string>('');

const renderedContent = computed(() => {
  if (!selectedRecord.value) return '';
  // 移除第一行标题(避免与 h1 重复)
  let content = selectedRecord.value.content.replace(/^#\s+.+\n\n?/, '');
  // 翻译实体类型
  content = content.replace(/\*\*类型\*\*:\s*(\w+)/g, (match, type) => {
    return `**类型**: ${translateEntityType(type)}`;
  });
  return marked(content);
});

const uniqueLinks = computed(() => {
  if (!selectedRecord.value) return [];
  const seen = new Set<string>();
  return selectedRecord.value.links.filter(link => {
    const key = `${link.type}-${link.target_name}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
});

const displayedBooks = computed(() => {
  if (!booksResult.value?.books) return [];
  return showAllBooks.value ? booksResult.value.books : booksResult.value.books.slice(0, 3);
});

onMounted(async () => {
  await loadFiles();
});

async function loadFiles() {
  loading.value = true;
  try {
    const response = await getFileList();
    files.value = response.files;
  } catch (error) {
    console.error('加载文件列表失败:', error);
  } finally {
    loading.value = false;
  }
}

async function handleFileSelect(fileId: string) {
  selectedFileId.value = fileId;
  selectedRecord.value = null;
  graphLoading.value = true;
  try {
    const response = await getCosmaData(fileId);
    cosmaRecords.value = response.records;
  } catch (error) {
    console.error('加载图谱数据失败:', error);
    cosmaRecords.value = [];
  } finally {
    graphLoading.value = false;
  }
}

function handleNodeClick(record: CosmaRecord) {
  selectedRecord.value = record;
  baikeResult.value = null;
  booksResult.value = null;
  showAllBooks.value = false;
}

async function handleSearchBaike() {
  if (!selectedRecord.value) return;

  searching.value = true;
  try {
    const result = await searchBaike(selectedRecord.value.title);
    baikeResult.value = result;
  } catch (error) {
    console.error('搜索百度百科失败:', error);
    baikeResult.value = { success: false, message: '搜索失败' };
  } finally {
    searching.value = false;
  }
}

async function handleSearchBooks() {
  if (!selectedRecord.value) return;

  searchingBooks.value = true;
  showAllBooks.value = false;
  try {
    const result = await searchBooks(selectedRecord.value.title);
    booksResult.value = result;
  } catch (error) {
    console.error('搜索图书失败:', error);
    booksResult.value = { success: false, message: '搜索失败' };
  } finally {
    searchingBooks.value = false;
  }
}

function handleOpenPDF() {
  if (!selectedFileId.value) return;

  // 构建 PDF 访问 URL - 使用环境变量中的 API 地址
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
  const pdfUrl = `${apiBaseUrl}/upload/pdf/${selectedFileId.value}`;

  // 在新窗口打开 PDF
  window.open(pdfUrl, '_blank');
}

function triggerFileUpload() {
  fileInput.value?.click();
}

// 停止进度轮询
function stopProgressPolling() {
  if (progressTimer !== null) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
}

// 开始进度轮询
async function startProgressPolling(fileId: string) {
  showProgress.value = true;
  uploadProgress.value = {
    file_id: fileId,
    status: 'processing',
    progress: 0,
    message: '开始处理...',
    updated_at: new Date().toISOString()
  };

  // 立即查询一次
  await pollProgress(fileId);

  // 每2秒轮询一次
  progressTimer = window.setInterval(async () => {
    await pollProgress(fileId);
  }, 2000);
}

// 轮询进度
async function pollProgress(fileId: string) {
  try {
    const progress = await getFileProgress(fileId);
    uploadProgress.value = progress;

    // 如果完成或失败,停止轮询
    if (progress.status === 'completed' || progress.status === 'failed') {
      stopProgressPolling();

      // 3秒后隐藏进度条
      setTimeout(() => {
        showProgress.value = false;
        uploadProgress.value = null;
      }, 3000);

      // 如果完成,刷新文件列表
      if (progress.status === 'completed') {
        await loadFiles();
      }
    }
  } catch (error) {
    console.error('获取进度失败:', error);
  }
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  uploading.value = true;
  try {
    const result = await uploadFile(file);
    uploadSuccessDialog.value?.show();

    // 开始轮询进度
    if (result.file_id) {
      await startProgressPolling(result.file_id);
    }
  } catch (error) {
    console.error('文件上传失败:', error);
    uploadErrorDialog.value?.show();
  } finally {
    uploading.value = false;
    if (fileInput.value) fileInput.value.value = '';
  }
}

// 显示重命名对话框
function handleRename(fileId: string, currentName: string) {
  pendingRenameFileId.value = fileId;
  pendingRenameFileName.value = currentName;
  renameDialog.value?.show(currentName);
}

// 确认重命名操作
async function confirmRename(newName: string) {
  const fileId = pendingRenameFileId.value;
  const currentName = pendingRenameFileName.value;

  if (!fileId || !newName || newName === currentName) return;

  try {
    await renameFile(fileId, newName);
    await loadFiles();
    renameSuccessDialog.value?.show();
  } catch (error) {
    console.error('重命名失败:', error);
    renameErrorDialog.value?.show();
  } finally {
    pendingRenameFileId.value = '';
    pendingRenameFileName.value = '';
  }
}

async function handleDelete(fileId: string) {
  pendingDeleteFileId.value = fileId;
  deleteDialog.value?.show();
}

async function confirmDelete() {
  const fileId = pendingDeleteFileId.value;
  if (!fileId) return;

  try {
    await deleteFile(fileId);
    if (selectedFileId.value === fileId) {
      selectedFileId.value = '';
      cosmaRecords.value = [];
      selectedRecord.value = null;
    }
    await loadFiles();
    deleteSuccessDialog.value?.show();
  } catch (error) {
    console.error('删除失败:', error);
    deleteErrorDialog.value?.show();
  } finally {
    pendingDeleteFileId.value = '';
  }
}

function formatFileId(fileId: string) {
  const parts = fileId.split('_');
  if (parts.length >= 2) {
    return `${parts[0].substring(0, 8)}... (${parts[1]})`;
  }
  return fileId.substring(0, 20) + '...';
}

function translateType(type: string): string {
  const typeMap: Record<string, string> = {
    'WORKS_AT': '任职于',
    'INVESTS_IN': '投资',
    'DEVELOPS': '开发',
    'COMPETES_WITH': '竞争',
    'PARTNERS_WITH': '合作',
    'BASED_ON': '基于',
    'LOCATED_IN': '位于',
    'PROMOTES': '推动',
    'LEADS': '领导',
    'GOVERNS': '治理',
    'PRESERVES': '保持',
    'PARTICIPATES_IN': '参与',
    'REPRESENTS': '代表',
    'BUILDING': '建设',
    'APPLIES': '应用',
    'ACHIEVES': '实现',
    'PROPOSES': '提出',
    'IMPLEMENTS': '实施',
    'GUIDES': '指导',
    'INHERITS': '继承',
    'SERVES': '服务',
    'UPHOLDS': '坚持',
    'OPPOSES': '反对',
    'BELONGS_TO': '属于',
    'ENACTS': '制定',
    'RELATED_TO': '相关',
    'MENTIONS': '提及',
    'CREATED_BY': '创建者',
    'OWNS': '拥有'
  };
  return typeMap[type] || type;
}

function translateEntityType(type: string): string {
  const entityTypeMap: Record<string, string> = {
    'Company': '公司',
    'Person': '人物',
    'Technology': '技术',
    'Product': '产品',
    'Organization': '组织',
    'Event': '事件',
    'Concept': '概念',
    'Location': '地点',
    'Document': '文档',
    'Theory': '理论',
    'Policy': '政策',
    'Party': '政党',
    'Government': '政府机构',
    'Law': '法律法规',
    'Meeting': '会议',
    'Movement': '运动',
    'Ideology': '意识形态',
    'Period': '时期',
    'unknown': '未知'
  };
  return entityTypeMap[type] || type;
}

function handleSettingsSaved() {
  console.log('LLM配置已保存');
  // 可以在这里添加提示信息或刷新相关数据
}
</script>

<style scoped>
/* 对照 Cosma 原版样式 */
.app {
  display: flex;
  overflow: hidden;
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
  font-family: system-ui, -apple-system, sans-serif;
  font-size: 1.4rem;
}

/* 左侧菜单 */
.menu {
  width: 300px;
  background: white;
  border-right: 1px solid #d8d8d8;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.menu header {
  padding: 1rem;
  border-bottom: 1px solid #f3f3f3;
}

.upload-btn {
  width: 100%;
  margin-top: 1rem;
  border: none;
  display: flex;
  padding: 0.75rem 1.5rem;
  background-color: #488aec;
  color: #ffffff;
  font-size: 0.75rem;
  line-height: 1rem;
  font-weight: 700;
  text-align: center;
  cursor: pointer;
  text-transform: uppercase;
  vertical-align: middle;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  user-select: none;
  gap: 0.75rem;
  box-shadow:
    0 4px 6px -1px #488aec31,
    0 2px 4px -1px #488aec17;
  transition: all 0.6s ease;
}

.upload-btn:hover {
  box-shadow:
    0 10px 15px -3px #488aec4f,
    0 4px 6px -2px #488aec17;
}

.upload-btn:focus,
.upload-btn:active {
  opacity: 0.85;
  box-shadow: none;
}

.upload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.upload-btn svg {
  width: 1.25rem;
  height: 1.25rem;
}

.settings-btn {
  width: 40px;
  height: 40px;
  margin-top: 1rem;
  border: none;
  display: flex;
  padding: 0.5rem;
  background-color: #6c757d;
  color: #ffffff;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  transition: all 0.3s ease;
  box-shadow:
    0 4px 6px -1px rgba(108, 117, 125, 0.2),
    0 2px 4px -1px rgba(108, 117, 125, 0.1);
}

.settings-btn:hover {
  background-color: #5a6268;
  box-shadow:
    0 10px 15px -3px rgba(108, 117, 125, 0.3),
    0 4px 6px -2px rgba(108, 117, 125, 0.1);
}

.settings-btn:active {
  opacity: 0.85;
  box-shadow: none;
}

.settings-btn svg {
  width: 1.25rem;
  height: 1.25rem;
}

.load-bar {
  height: 4px;
  background: #fafafa;
  border-radius: 2px;
  overflow: hidden;
}

.load-bar-value {
  height: 100%;
  background: #147899;
  width: 0%;
}

.menu-index {
  padding: 1rem;
}

.menu-title {
  font-weight: 600;
  font-size: 1.3rem;
  margin-bottom: 1rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.list-expand-icon {
  width: 0.96em;
  height: 0.96em;
  color: #999;
  transition: transform 0.3s ease;
}

details[open] .list-expand-icon {
  transform: rotate(90deg);
  color: #147899;
}

.badge {
  background: transparent;
  padding: 0;
  border: 1px solid #147899;
  border-radius: 4px;
  font-size: 0.85rem;
  color: #147899;
  min-width: 1.6em;
  height: 1.6em;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
  transition: all 0.3s ease;
}


.menu-index-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.menu-index-list li {
  margin-bottom: 0.6rem;
  cursor: pointer;
  position: relative;
}

.menu-index-list li:hover .file-actions {
  opacity: 1;
}

.menu-index-list li:hover a {
  transform: translateX(3px);
  box-shadow: 0 2px 8px rgba(20, 120, 153, 0.1);
}

.menu-index-list li.active a {
  background: #e8f4f8;
  border-left: 3px solid #147899;
  box-shadow: 0 2px 6px rgba(20, 120, 153, 0.15);
}

.menu-index-list a {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.8rem 0.7rem;
  text-decoration: none;
  color: #333;
  border-radius: 8px;
  border-left: 3px solid transparent;
  transition: all 0.3s ease;
  font-size: 0.98rem;
}

.menu-index-list a > span:nth-child(2) {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-index-list li:hover a {
  padding-right: 70px;
}

.menu-index-list a:hover {
  background: #f8f9fa;
}

.file-actions {
  position: absolute;
  right: 0.6rem;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  gap: 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.file-actions .rename-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}

.file-actions .rename-btn svg {
  width: 66%;
  fill: #B5BAC1;
}

.file-actions .rename-btn:hover {
  background-color: rgb(255, 170, 51);
  overflow: visible;
}

.file-actions .rename-btn:hover svg path {
  fill: #fff;
}

.file-actions .rename-btn:active {
  transform: scale(0.98);
}

.file-actions .rename-btn .tooltip {
  position: absolute;
  top: -32px;
  background-color: rgb(41, 41, 41);
  color: white;
  border-radius: 5px;
  font-size: 11px;
  padding: 4px 8px;
  font-weight: 600;
  box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.15);
  white-space: nowrap;
  opacity: 0;
  transition: all 0.3s;
  pointer-events: none;
}

.file-actions .rename-btn .tooltip::before {
  position: absolute;
  width: 6px;
  height: 6px;
  transform: rotate(45deg);
  content: "";
  background-color: rgb(41, 41, 41);
  bottom: -3px;
  left: 50%;
  margin-left: -3px;
}

.file-actions .rename-btn:hover .tooltip {
  opacity: 1;
}

.file-actions .delete-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}

.file-actions .delete-btn svg {
  width: 66%;
}

.file-actions .delete-btn:hover {
  background-color: rgb(237, 56, 56);
  overflow: visible;
}

.file-actions .delete-btn .bin path {
  transition: all 0.2s;
}

.file-actions .delete-btn:hover .bin path {
  fill: #fff;
}

.file-actions .delete-btn:active {
  transform: scale(0.98);
}

.file-actions .delete-btn .tooltip {
  position: absolute;
  top: -32px;
  background-color: rgb(41, 41, 41);
  color: white;
  border-radius: 5px;
  font-size: 11px;
  padding: 4px 8px;
  font-weight: 600;
  box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.15);
  white-space: nowrap;
  opacity: 0;
  transition: all 0.3s;
  pointer-events: none;
}

.file-actions .delete-btn .tooltip::before {
  position: absolute;
  width: 6px;
  height: 6px;
  transform: rotate(45deg);
  content: "";
  background-color: rgb(41, 41, 41);
  bottom: -3px;
  left: 50%;
  margin-left: -3px;
}

.file-actions .delete-btn:hover .tooltip {
  opacity: 1;
}

.record-type-points {
  color: #147899;
  font-size: 0.9rem;
}

.menu-index-list li.active .record-type-points {
  color: #ff6b6b;
}

/* 中间图谱区域 */
.graph-wrapper {
  flex: 1;
  position: relative;
  background: #ffffff;
  overflow: hidden;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.spinner {
  font-size: 1.2rem;
  color: #147899;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}

.loading {
  padding: 1rem;
  text-align: center;
  color: #666;
}

/* 右侧记录详情 */
.record-container {
  width: 400px;
  background: white;
  border-left: 1px solid #d8d8d8;
  overflow-y: auto;
  padding: 2rem;
}

.record {
  display: none;
}

.record.active {
  display: block;
}

.record header h1 {
  margin: 0 0 1rem 0;
  font-size: 1.8rem;
  color: #333;
}

.record header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.search-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #147899;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.search-btn:hover:not(:disabled) {
  background: #0f5f7a;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(20, 120, 153, 0.3);
}

.search-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.search-btn svg {
  width: 16px;
  height: 16px;
}

.search-buttons {
  display: flex;
  gap: 0.5rem;
}

.books-btn {
  background: #ff6b6b;
}

.books-btn:hover:not(:disabled) {
  background: #ee5a52;
}

.pdf-btn {
  background: #e7298a;
}

.pdf-btn:hover {
  background: #c91f73;
}

.baike-result {
  margin: 1.5rem 0;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 3px solid #147899;
}

.baike-result h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  color: #147899;
}

.baike-summary {
  line-height: 1.6;
  color: #333;
  margin-bottom: 1rem;
}

.baike-info {
  margin: 1rem 0;
  padding: 0.8rem;
  background: white;
  border-radius: 6px;
}

.info-item {
  padding: 0.4rem 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 0.9rem;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item strong {
  color: #666;
  margin-right: 0.5rem;
}

.baike-link {
  display: inline-block;
  margin-top: 0.8rem;
  color: #147899;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s ease;
}

.baike-link:hover {
  color: #0f5f7a;
}

.baike-error {
  color: #999;
  font-style: italic;
}

.books-result {
  margin: 1.5rem 0;
  padding: 1rem;
  background: #fff5f5;
  border-radius: 8px;
  border-left: 3px solid #ff6b6b;
}

.books-result h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  color: #ff6b6b;
}

.book-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  margin-bottom: 1rem;
  background: white;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.book-item:hover {
  box-shadow: 0 2px 8px rgba(255, 107, 107, 0.2);
  transform: translateY(-2px);
}

.book-cover {
  width: 80px;
  height: 110px;
  object-fit: cover;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.book-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.book-info h4 {
  margin: 0;
  font-size: 1rem;
  color: #333;
  line-height: 1.4;
}

.book-author {
  margin: 0;
  font-size: 0.9rem;
  color: #666;
}

.book-publisher {
  margin: 0;
  font-size: 0.85rem;
  color: #888;
}

.book-isbn {
  margin: 0;
  font-size: 0.85rem;
  color: #888;
}

.book-description {
  margin: 0.5rem 0 0 0;
  font-size: 0.85rem;
  color: #555;
  line-height: 1.5;
  max-height: 3em;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.book-link {
  display: inline-block;
  margin-top: auto;
  color: #ff6b6b;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.9rem;
  transition: color 0.3s ease;
}

.book-link:hover {
  color: #ee5a52;
}

.expand-button {
  display: block;
  width: 100%;
  margin-top: 1rem;
  padding: 0.8rem;
  background: white;
  border: 1px solid #ff6b6b;
  border-radius: 6px;
  color: #ff6b6b;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.expand-button:hover {
  background: #ff6b6b;
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(255, 107, 107, 0.3);
}

.books-total {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #ffe0e0;
  color: #666;
  font-size: 0.9rem;
  text-align: center;
}

.books-error {
  color: #999;
  font-style: italic;
}

.record-content {
  line-height: 1.6;
  color: #333;
}

.record footer {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #f3f3f3;
}

.record footer h3 {
  font-size: 1.3rem;
  margin: 0 0 1rem 0;
}

.record footer ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.record footer li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #f3f3f3;
}

.record footer li:last-child {
  border-bottom: none;
}

.empty-record {
  color: #666;
  text-align: center;
}
</style>
