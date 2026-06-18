-- 初始化两个数据库 Schema
-- 由 MySQL 容器启动时自动执行

CREATE DATABASE IF NOT EXISTS iptc_main
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS iptc_practice
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 授权 root 访问两个 Schema（容器内 root 默认有权限，此处为明确声明）
GRANT ALL PRIVILEGES ON iptc_main.* TO 'root'@'%';
GRANT ALL PRIVILEGES ON iptc_practice.* TO 'root'@'%';
FLUSH PRIVILEGES;
