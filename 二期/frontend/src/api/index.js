import request from '@/utils/request'
import collectorRequest from '@/utils/collectorRequest'

// 认证相关API
export const authAPI = {
  // 登录
  login(data) {
    return request.post('/auth/login', data)
  },
  // 登出
  logout() {
    return request.post('/auth/logout')
  },
  // 获取当前用户信息
  getCurrentUser() {
    return request.get('/auth/me')
  },
  // 修改密码
  changePassword(data) {
    return request.post('/auth/change-password', data)
  },
  // 用户自助注册
  selfRegister(data) {
    return request.post('/auth/self-register', data)
  },
  // 获取教师列表（公开）
  getTeachers() {
    return request.get('/auth/teachers')
  },
  // 获取我的学生列表
  getMyStudents() {
    return request.get('/auth/my-students')
  },
  // 修改指导教师
  updateTeacher(teacherId) {
    return request.put('/auth/update-teacher', null, { params: { teacher_id: teacherId } })
  },
  // 更新个人资料
  updateProfile(data) {
    return request.put('/auth/profile', data)
  }
}

// 知识点相关API
export const knowledgeAPI = {
  // 获取知识点列表
  getList(params) {
    return request.get('/knowledge-points', { params })
  },
  // 获取知识点详情
  getDetail(id) {
    return request.get(`/knowledge-points/${id}`)
  }
}

// 实践方案相关API
export const practiceAPI = {
  // 生成实践方案
  generatePlan(data) {
    return request.post('/practice/plans/generate', data)
  },
  // 创建自由申请方案（学生自主填写）
  createFreePlan(data) {
    return request.post('/practice/plans/free', data)
  },
  // 查询任务状态
  getTaskStatus(taskId) {
    return request.get(`/practice/plans/task/${taskId}`)
  },
  // 获取方案详情
  getPlanDetail(id) {
    return request.get(`/practice/plans/${id}`)
  },
  // 获取我的方案列表
  getMyPlans(params) {
    return request.get('/practice/plans', { params })
  },
  // 删除方案
  deletePlan(id) {
    return request.delete(`/practice/plans/${id}`)
  },
  // 设置截止日期
  setDeadline(id, deadline) {
    return request.put(`/practice/plans/${id}/deadline`, null, { params: { deadline } })
  }
}

// 实践提交相关API
export const submissionAPI = {
  // 创建提交
  create(data) {
    return request.post('/submissions', data)
  },
  // 获取提交列表
  getList(params) {
    return request.get('/submissions', { params })
  },
  // 获取提交详情
  getDetail(id) {
    return request.get(`/submissions/${id}`)
  },
  // 更新提交
  update(id, data) {
    return request.put(`/submissions/${id}`, data)
  },
  // 上传文件
  uploadFiles(id, files) {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    return request.post(`/submissions/${id}/files`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  // 正式提交
  submit(id) {
    return request.post(`/submissions/${id}/submit`)
  },
  // 删除提交
  delete(id) {
    return request.delete(`/submissions/${id}`)
  },
  // 获取优秀作品墙
  getShowcase(params) {
    return request.get('/submissions/showcase/list', { params })
  },
  // 设置展示状态
  toggleShowcase(id, is_showcased) {
    return request.put(`/submissions/${id}/showcase`, null, { params: { is_showcased } })
  },
  // 一键生成报告（返回 docx 文件 blob）
  generateReport(id) {
    return request.get(`/submissions/${id}/report`, { responseType: 'arraybuffer' })
  }
}

// 场馆相关API
export const venueAPI = {
  // 获取场馆列表
  getList(params) {
    return request.get('/venues', { params })
  },
  // 获取场馆详情
  getDetail(id) {
    return request.get(`/venues/${id}`)
  },
  // 获取场馆类别列表
  getCategories(params) {
    return request.get('/venues/categories', { params })
  },
  // 获取场馆地区列表
  getRegions(params) {
    return request.get('/venues/regions', { params })
  }
}

// 审核相关API
export const reviewAPI = {
  // 获取待审核列表
  getPendingList(params) {
    return request.get('/reviews/pending', { params })
  },
  // 提交审核结果
  create(data) {
    return request.post('/reviews', data)
  },
  // 获取审核历史
  getHistory(params) {
    return request.get('/reviews/history', { params })
  },
  // 获取审核详情
  getDetail(id) {
    return request.get(`/reviews/${id}`)
  },
  // 获取统计数据
  getStatistics() {
    return request.get('/reviews/stats/summary')
  },
  // AI辅助评分
  getAISuggestion(submissionId) {
    return request.get(`/reviews/ai-suggest/${submissionId}`)
  }
}

// 批注相关API
export const annotationAPI = {
  // 添加批注
  create(data) {
    return request.post('/annotations', data)
  },
  // 获取批注列表
  getList(submissionId) {
    return request.get(`/annotations/${submissionId}`)
  },
  // 删除批注
  delete(annotationId) {
    return request.delete(`/annotations/${annotationId}`)
  }
}

// 一期案例库API
export const caseAPI = {
  getList(params) {
    return collectorRequest.get('/iptc/cases', { params })
  },
  getDetail(id) {
    return collectorRequest.get(`/iptc/cases/${id}`)
  },
  getKnowledgePoints() {
    return collectorRequest.get('/iptc/knowledge-points')
  },
  getKnowledgeTree() {
    return collectorRequest.get('/iptc/knowledge-tree')
  },
  getKnowledgeTreeByParams(params) {
    return collectorRequest.get('/iptc/knowledge-tree', { params })
  },
  getStatistics() {
    return collectorRequest.get('/iptc/statistics')
  },
  getMessageCandidates(params) {
    return collectorRequest.get('/iptc/candidates/messages', { params })
  },
  getMatchCandidates(params) {
    return collectorRequest.get('/iptc/candidates/matches', { params })
  },
  getCaseCandidates(params) {
    return collectorRequest.get('/iptc/candidates/cases', { params })
  },
  getTaskStatus(taskId) {
    return collectorRequest.get(`/iptc/tasks/${taskId}`)
  }
}

// 一期采集器任务API
export const collectorAPI = {
  getTaskStatus(sourceName, taskId) {
    return collectorRequest.get(`/collectors/${encodeURIComponent(sourceName)}/task/${taskId}`)
  }
}

// 一期知识图谱API
export const graphAPI = {
  getBooks() {
    return collectorRequest.get('/knowledge-graph/books')
  },
  getGraphData(bookId) {
    const params = bookId ? { book_id: bookId } : {}
    return collectorRequest.get('/knowledge-graph/data', { params })
  },
  getKnowledgePointDetail(kpId) {
    return collectorRequest.get(`/knowledge-graph/knowledge-point/${kpId}`)
  }
}

// 管理员API
export const adminAPI = {
  getOverview() {
    return request.get('/admin/overview')
  },
  getMessageSources() {
    return request.get('/admin/message-sources')
  },
  getMatchingStatus() {
    return request.get('/admin/matching-status')
  },
  getCollectors() {
    return request.get('/admin/collectors')
  },
  triggerCollector(name) {
    return request.post(`/admin/collectors/${encodeURIComponent(name)}/trigger`)
  },
  triggerMatching(data = {}) {
    return request.post('/admin/trigger-matching', data)
  },
  triggerCaseGeneration(data = {}) {
    return request.post('/admin/trigger-case-generation', data)
  },
  getUsers(params) {
    return request.get('/admin/users', { params })
  },
  updateUserRole(userId, role) {
    return request.put(`/admin/users/${userId}/role`, null, { params: { role } })
  },
  getPractices(params) {
    return request.get('/admin/practices', { params })
  },
  getVenues() {
    return request.get('/admin/venues')
  }
}
