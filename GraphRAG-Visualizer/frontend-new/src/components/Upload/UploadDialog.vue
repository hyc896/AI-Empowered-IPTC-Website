<!--
  文件上传对话框组件
  处理 PDF 文件上传和页面范围选择
-->
<template>
  <el-dialog
    v-model="dialogVisible"
    title="上传 PDF 文件"
    width="600px"
    @close="handleClose"
  >
    <el-form :model="form" label-width="100px">
      <!-- 文件上传 -->
      <el-form-item label="选择文件">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-exceed="handleExceed"
          accept=".pdf"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">只支持 PDF 文件</div>
          </template>
        </el-upload>
      </el-form-item>

      <!-- 页面范围 -->
      <el-form-item label="页面范围">
        <el-col :span="11">
          <el-input-number
            v-model="form.pageStart"
            :min="1"
            :max="form.pageEnd"
            placeholder="起始页"
          />
        </el-col>
        <el-col :span="2" class="text-center">-</el-col>
        <el-col :span="11">
          <el-input-number
            v-model="form.pageEnd"
            :min="form.pageStart"
            placeholder="结束页"
          />
        </el-col>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button
        type="primary"
        :loading="uploading"
        :disabled="!selectedFile"
        @click="handleUpload"
      >
        上传并提取
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import type { UploadInstance, UploadFile } from 'element-plus'
import { uploadPDF } from '@/api/upload'
import { extractEntities } from '@/api/extract'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: [fileId: string]
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)
const uploading = ref(false)

const form = ref({
  pageStart: 1,
  pageEnd: 20
})

const handleFileChange = (file: UploadFile) => {
  selectedFile.value = file.raw || null
}

const handleExceed = () => {
  ElMessage.warning('只能上传一个文件')
}

const handleUpload = async () => {
  if (!selectedFile.value) return

  uploading.value = true
  try {
    // 1. 上传文件
    const uploadResponse = await uploadPDF(
      selectedFile.value,
      form.value.pageStart,
      form.value.pageEnd
    )
    ElMessage.success('文件上传成功，正在提取实体...')

    // 2. 提取实体和关系
    await extractEntities({
      file_id: uploadResponse.file_id,
      text: uploadResponse.text,
      page_range: uploadResponse.current_range,
      language: 'zh'
    })
    ElMessage.success('实体提取完成')

    emit('success', uploadResponse.file_id)
    handleClose()
  } catch (error) {
    ElMessage.error('处理失败')
    console.error(error)
  } finally {
    uploading.value = false
  }
}

const handleClose = () => {
  dialogVisible.value = false
  selectedFile.value = null
  uploadRef.value?.clearFiles()
  form.value = { pageStart: 1, pageEnd: 20 }
}
</script>

<style scoped>
.text-center {
  text-align: center;
}
</style>
