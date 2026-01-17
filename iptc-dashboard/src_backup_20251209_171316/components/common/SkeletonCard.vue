<template>
  <div class="skeleton-card">
    <div class="skeleton-header skeleton-shine"></div>
    <div class="skeleton-body">
      <div class="skeleton-title skeleton-shine"></div>
      <div class="skeleton-text skeleton-shine"></div>
      <div class="skeleton-text skeleton-shine" style="width: 85%"></div>
      <div class="skeleton-text skeleton-shine" style="width: 60%"></div>
    </div>
    <div class="skeleton-footer skeleton-shine"></div>
  </div>
</template>

<style scoped lang="scss">
.skeleton-card {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);

  .skeleton-header {
    height: 120px;
    background: linear-gradient(135deg, #f0f0f0 0%, #e0e0e0 100%);
  }

  .skeleton-body {
    padding: 20px;

    .skeleton-title {
      height: 24px;
      border-radius: 4px;
      margin-bottom: 16px;
      width: 80%;
    }

    .skeleton-text {
      height: 16px;
      border-radius: 4px;
      margin-bottom: 10px;
      width: 100%;
    }
  }

  .skeleton-footer {
    height: 50px;
    margin: 0 20px 20px;
    border-radius: 8px;
  }

  .skeleton-shine {
    background: linear-gradient(
      90deg,
      #f0f0f0 25%,
      #e0e0e0 50%,
      #f0f0f0 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
}
</style>
