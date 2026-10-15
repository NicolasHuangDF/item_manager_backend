/*
 Navicat Premium Dump SQL

 Source Server         : 本地数据库
 Source Server Type    : MySQL
 Source Server Version : 80021 (8.0.21)
 Source Host           : localhost:3306
 Source Schema         : item_manager

 Target Server Type    : MySQL
 Target Server Version : 80021 (8.0.21)
 File Encoding         : 65001

 Date: 15/10/2026 09:48:22
*/

SET NAMES utf8mb4;

SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '用户名，唯一',
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '邮箱，唯一',
  `phone` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '手机号，唯一',
  `password_hash` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码哈希',
  `display_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '显示名称',
  `avatar_url` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '头像URL',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '状态：active/disabled/deleted',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at` datetime(3) NULL DEFAULT NULL COMMENT '软删除时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_users_username`(`username` ASC) USING BTREE,
  UNIQUE INDEX `uk_users_email`(`email` ASC) USING BTREE,
  UNIQUE INDEX `uk_users_phone`(`phone` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户账号表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for auth_tokens
-- ----------------------------
DROP TABLE IF EXISTS `auth_tokens`;
CREATE TABLE `auth_tokens`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `user_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户ID',
  `token_hash` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '令牌哈希',
  `type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '类型：access/refresh/session/api_key',
  `expires_at` datetime(3) NULL DEFAULT NULL COMMENT '过期时间',
  `revoked_at` datetime(3) NULL DEFAULT NULL COMMENT '撤销时间',
  `device_info` json NULL COMMENT '设备信息JSON',
  `ip` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'IP地址',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `last_used_at` datetime(3) NULL DEFAULT NULL COMMENT '最后使用时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_auth_tokens_user`(`user_id` ASC) USING BTREE,
  INDEX `idx_auth_tokens_expires`(`expires_at` ASC) USING BTREE,
  CONSTRAINT `fk_auth_tokens_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '认证令牌/会话表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for properties
-- ----------------------------
DROP TABLE IF EXISTS `properties`;
CREATE TABLE `properties`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '房屋名称',
  `address` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '地址',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '房屋类型',
  `sort_order` int NOT NULL DEFAULT 0 COMMENT '排序',
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '备注',
  `created_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '创建人用户ID',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at` datetime(3) NULL DEFAULT NULL COMMENT '软删除时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_properties_created_by`(`created_by` ASC) USING BTREE,
  CONSTRAINT `fk_properties_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '房屋表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for settings
-- ----------------------------
DROP TABLE IF EXISTS `settings`;
CREATE TABLE `settings`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `scope` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '范围：system/user/property',
  `owner_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '00000000000000000000000000000000' COMMENT '所有者ID：system为全零UUID，user为users.id，property为properties.id',
  `key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '配置键',
  `value` json NULL COMMENT '配置值JSON',
  `updated_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '更新人用户ID',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_settings_scope_owner_key`(`scope` ASC, `owner_id` ASC, `key` ASC) USING BTREE,
  INDEX `fk_settings_updated_by`(`updated_by` ASC) USING BTREE,
  CONSTRAINT `fk_settings_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '统一配置表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for attachments
-- ----------------------------
DROP TABLE IF EXISTS `attachments`;
CREATE TABLE `attachments`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属房屋ID',
  `owner_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属类型：item/item_batch/container/property/reminder',
  `owner_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属对象ID',
  `file_path` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '文件名',
  `mime_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'MIME类型',
  `file_size` bigint NULL DEFAULT NULL COMMENT '文件大小',
  `uploaded_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '上传人用户ID',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_attachments_property`(`property_id` ASC) USING BTREE,
  INDEX `idx_attachments_owner`(`owner_type` ASC, `owner_id` ASC) USING BTREE,
  INDEX `fk_attachments_uploaded_by`(`uploaded_by` ASC) USING BTREE,
  CONSTRAINT `fk_attachments_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_attachments_uploaded_by` FOREIGN KEY (`uploaded_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '附件表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for audit_logs
-- ----------------------------
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '房屋ID（可空）',
  `user_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '用户ID（可空）',
  `action` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作',
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '实体类型',
  `entity_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '实体ID',
  `before_data` json NULL COMMENT '变更前数据JSON',
  `after_data` json NULL COMMENT '变更后数据JSON',
  `ip` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'IP地址',
  `user_agent` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '用户代理',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_audit_logs_property_created`(`property_id` ASC, `created_at` ASC) USING BTREE,
  INDEX `idx_audit_logs_user_created`(`user_id` ASC, `created_at` ASC) USING BTREE,
  INDEX `idx_audit_logs_entity`(`entity_type` ASC, `entity_id` ASC) USING BTREE,
  CONSTRAINT `fk_audit_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '操作审计表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for containers
-- ----------------------------
DROP TABLE IF EXISTS `containers`;
CREATE TABLE `containers`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属房屋ID',
  `parent_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '父容器ID',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '容器名称',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'other' COMMENT '容器类型：room/cabinet/drawer/shelf/grid/box/fridge/freezer/appliance/other',
  `qr_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '二维码',
  `icon` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '图标',
  `color` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '颜色',
  `sort_order` int NOT NULL DEFAULT 0 COMMENT '排序',
  `attributes` json NULL COMMENT '扩展属性JSON',
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用：0否1是',
  `created_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '创建人用户ID',
  `updated_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '更新人用户ID',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at` datetime(3) NULL DEFAULT NULL COMMENT '软删除时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_containers_property_parent`(`property_id` ASC, `parent_id` ASC) USING BTREE,
  INDEX `idx_containers_property_type`(`property_id` ASC, `type` ASC) USING BTREE,
  INDEX `idx_containers_qr_code`(`qr_code` ASC) USING BTREE,
  INDEX `fk_containers_parent`(`parent_id` ASC) USING BTREE,
  INDEX `fk_containers_created_by`(`created_by` ASC) USING BTREE,
  INDEX `fk_containers_updated_by`(`updated_by` ASC) USING BTREE,
  CONSTRAINT `fk_containers_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_containers_parent` FOREIGN KEY (`parent_id`) REFERENCES `containers` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_containers_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_containers_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '容器表：房间、橱柜、抽屉、格子、盒子、冰箱、冰柜、电器等' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for notification_channels
-- ----------------------------
DROP TABLE IF EXISTS `notification_channels`;
CREATE TABLE `notification_channels`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `user_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户ID',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '房屋ID（可空）',
  `type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '类型：email/push/bark/telegram/webhook',
  `config` json NULL COMMENT '配置JSON',
  `is_enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用：0否1是',
  `verified_at` datetime(3) NULL DEFAULT NULL COMMENT '验证时间',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_nc_user`(`user_id` ASC) USING BTREE,
  INDEX `idx_nc_property`(`property_id` ASC) USING BTREE,
  CONSTRAINT `fk_nc_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_nc_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '通知渠道表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for property_invitations
-- ----------------------------
DROP TABLE IF EXISTS `property_invitations`;
CREATE TABLE `property_invitations`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '房屋ID',
  `inviter_user_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '邀请人用户ID',
  `invitee_email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '被邀请人邮箱',
  `invitee_phone` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '被邀请人手机号',
  `token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '邀请令牌',
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'member' COMMENT '邀请角色：admin/member/guest',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '状态：pending/accepted/expired/cancelled',
  `expires_at` datetime(3) NOT NULL COMMENT '过期时间',
  `accepted_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '接受人用户ID',
  `accepted_at` datetime(3) NULL DEFAULT NULL COMMENT '接受时间',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_property_invitations_token`(`token` ASC) USING BTREE,
  INDEX `idx_pi_property`(`property_id` ASC) USING BTREE,
  INDEX `idx_pi_status`(`status` ASC, `expires_at` ASC) USING BTREE,
  INDEX `fk_pi_inviter`(`inviter_user_id` ASC) USING BTREE,
  INDEX `fk_pi_accepted_by`(`accepted_by` ASC) USING BTREE,
  CONSTRAINT `fk_pi_accepted_by` FOREIGN KEY (`accepted_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_pi_inviter` FOREIGN KEY (`inviter_user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_pi_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '房屋邀请表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for property_members
-- ----------------------------
DROP TABLE IF EXISTS `property_members`;
CREATE TABLE `property_members`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '房屋ID',
  `user_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户ID',
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'member' COMMENT '角色：admin/member/guest',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '状态：active/invited/removed',
  `joined_at` datetime(3) NULL DEFAULT NULL COMMENT '加入时间',
  `invited_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '邀请人用户ID',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_property_members`(`property_id` ASC, `user_id` ASC) USING BTREE,
  INDEX `idx_property_members_user`(`user_id` ASC) USING BTREE,
  INDEX `idx_property_members_role`(`property_id` ASC, `role` ASC) USING BTREE,
  INDEX `fk_pm_invited_by`(`invited_by` ASC) USING BTREE,
  CONSTRAINT `fk_pm_invited_by` FOREIGN KEY (`invited_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_pm_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_pm_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '房屋成员关系表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for tags
-- ----------------------------
DROP TABLE IF EXISTS `tags`;
CREATE TABLE `tags`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '来源房屋ID，仅用于追踪，审核通过后可为空',
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标签名称',
  `color` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '颜色',
  `created_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '创建人用户ID，系统预置可为空',
  `is_public` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否公共：0私有1公共',
  `review_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '审核状态：pending/approved/rejected',
  `reviewed_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '审核人用户ID',
  `reviewed_at` datetime(3) NULL DEFAULT NULL COMMENT '审核时间',
  `review_remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '审核备注',
  `published_at` datetime(3) NULL DEFAULT NULL COMMENT '转为公共的时间',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at` datetime(3) NULL DEFAULT NULL COMMENT '软删除时间',
  `name_public_unique` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci GENERATED ALWAYS AS ((case when ((`is_public` = 1) and (`deleted_at` is null)) then `name` else NULL end)) STORED COMMENT '公共命名唯一键' NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_tags_public_name`(`name_public_unique` ASC) USING BTREE,
  INDEX `idx_tags_review`(`review_status` ASC, `is_public` ASC) USING BTREE,
  INDEX `idx_tags_created_by`(`created_by` ASC) USING BTREE,
  INDEX `idx_tags_public`(`is_public` ASC, `deleted_at` ASC) USING BTREE,
  INDEX `fk_tags_property`(`property_id` ASC) USING BTREE,
  INDEX `fk_tags_reviewed_by`(`reviewed_by` ASC) USING BTREE,
  CONSTRAINT `fk_tags_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_tags_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_tags_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '标签表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for categories
-- 注意：这里暂时不添加 fk_categories_unit 外键，等 units 创建后再补充
-- ----------------------------
DROP TABLE IF EXISTS `categories`;
CREATE TABLE `categories`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '来源房屋ID，仅用于追踪，审核通过后可为空',
  `parent_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '父分类ID',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '分类名称',
  `icon` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '图标',
  `default_unit_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '默认单位ID',
  `default_low_stock_threshold` decimal(12, 3) NULL DEFAULT NULL COMMENT '默认低库存阈值',
  `default_expiry_warning_days` int NULL DEFAULT NULL COMMENT '默认过期提前提醒天数',
  `sort_order` int NOT NULL DEFAULT 0 COMMENT '排序',
  `created_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '创建人用户ID，系统预置可为空',
  `is_public` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否公共：0私有1公共',
  `review_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '审核状态：pending/approved/rejected',
  `reviewed_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '审核人用户ID',
  `reviewed_at` datetime(3) NULL DEFAULT NULL COMMENT '审核时间',
  `review_remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '审核备注',
  `published_at` datetime(3) NULL DEFAULT NULL COMMENT '转为公共的时间',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at` datetime(3) NULL DEFAULT NULL COMMENT '软删除时间',
  `name_public_unique` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci GENERATED ALWAYS AS ((case when ((`is_public` = 1) and (`deleted_at` is null)) then `name` else NULL end)) STORED COMMENT '公共命名唯一键，仅公共记录参与唯一约束' NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_categories_public_name`(`name_public_unique` ASC) USING BTREE,
  INDEX `idx_categories_property_parent`(`property_id` ASC, `parent_id` ASC) USING BTREE,
  INDEX `idx_categories_review`(`review_status` ASC, `is_public` ASC) USING BTREE,
  INDEX `idx_categories_created_by`(`created_by` ASC) USING BTREE,
  INDEX `idx_categories_public`(`is_public` ASC, `deleted_at` ASC) USING BTREE,
  INDEX `fk_categories_parent`(`parent_id` ASC) USING BTREE,
  INDEX `fk_categories_unit`(`default_unit_id` ASC) USING BTREE,
  INDEX `fk_categories_reviewed_by`(`reviewed_by` ASC) USING BTREE,
  CONSTRAINT `fk_categories_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_categories_parent` FOREIGN KEY (`parent_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_categories_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_categories_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
  -- 注意：此处省略了 fk_categories_unit，稍后通过 ALTER TABLE 添加
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '物品分类表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for units
-- ----------------------------
DROP TABLE IF EXISTS `units`;
CREATE TABLE `units`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '来源房屋ID，仅用于追踪，审核通过后可为空，建议is_public=0时保留',
  `category_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '关联物品分类ID；NULL 表示通用单位，非 NULL 表示仅限该分类使用',
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '单位名称',
  `symbol` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '单位符号',
  `decimal_places` int NOT NULL DEFAULT 0 COMMENT '小数位数',
  `created_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '创建人用户ID，系统预置可为空',
  `is_public` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否公共：0私有1公共',
  `review_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '审核状态：pending/approved/rejected',
  `reviewed_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '审核人用户ID',
  `reviewed_at` datetime(3) NULL DEFAULT NULL COMMENT '审核时间',
  `review_remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '审核备注',
  `published_at` datetime(3) NULL DEFAULT NULL COMMENT '转为公共的时间',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at` datetime(3) NULL DEFAULT NULL COMMENT '软删除时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_units_review`(`review_status` ASC, `is_public` ASC) USING BTREE,
  INDEX `idx_units_created_by`(`created_by` ASC) USING BTREE,
  INDEX `idx_units_public`(`is_public` ASC, `deleted_at` ASC) USING BTREE,
  INDEX `idx_units_scope`(`is_public` ASC, `category_id` ASC, `property_id` ASC) USING BTREE COMMENT '查询可用单位索引',
  INDEX `fk_units_property`(`property_id` ASC) USING BTREE,
  INDEX `fk_units_reviewed_by`(`reviewed_by` ASC) USING BTREE,
  CONSTRAINT `fk_units_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_units_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_units_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_units_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '单位表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- 补充 categories 对 units 的外键（解决循环依赖）
-- ----------------------------
ALTER TABLE `categories`
  ADD CONSTRAINT `fk_categories_unit` FOREIGN KEY (`default_unit_id`) REFERENCES `units` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT;

DELIMITER $$

DROP TRIGGER IF EXISTS `trg_units_public_unique_before_insert`$$

CREATE TRIGGER `trg_units_public_unique_before_insert`
BEFORE INSERT ON `units`
FOR EACH ROW
BEGIN
  IF NEW.`is_public` = 1 AND NEW.`deleted_at` IS NULL THEN
    IF NEW.`category_id` IS NULL THEN
      IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '通用单位名称必须全局唯一';
      END IF;
    ELSE
      IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL AND `category_id` IS NULL) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '不能与通用单位同名';
      END IF;
      IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL AND `category_id` = NEW.`category_id`) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '该分类下已存在同名公共单位';
      END IF;
    END IF;
  END IF;
END$$

-- UPDATE 触发器逻辑类似，需排除自身 ID
DROP TRIGGER IF EXISTS `trg_units_public_unique_before_update`$$
CREATE TRIGGER `trg_units_public_unique_before_update`
BEFORE UPDATE ON `units`
FOR EACH ROW
BEGIN
  IF NEW.`is_public` = 1 AND NEW.`deleted_at` IS NULL THEN
    IF NEW.`category_id` IS NULL THEN
      IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL AND `id` <> NEW.`id`) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '通用单位名称必须全局唯一';
      END IF;
    ELSE
      IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL AND `category_id` IS NULL AND `id` <> NEW.`id`) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '不能与通用单位同名';
      END IF;
      IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL AND `category_id` = NEW.`category_id` AND `id` <> NEW.`id`) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '该分类下已存在同名公共单位';
      END IF;
    END IF;
  END IF;
END$$

DELIMITER ;

-- ----------------------------
-- Table structure for notification_preferences
-- ----------------------------
DROP TABLE IF EXISTS `notification_preferences`;
CREATE TABLE `notification_preferences`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `user_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户ID',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '房屋ID（可空）',
  `event_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '事件类型',
  `channel_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '渠道ID',
  `enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用：0否1是',
  `advance_days` int NULL DEFAULT NULL COMMENT '提前天数',
  `quiet_hours` json NULL COMMENT '免打扰时段JSON',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_np_user`(`user_id` ASC) USING BTREE,
  INDEX `idx_np_property`(`property_id` ASC) USING BTREE,
  INDEX `fk_np_channel`(`channel_id` ASC) USING BTREE,
  CONSTRAINT `fk_np_channel` FOREIGN KEY (`channel_id`) REFERENCES `notification_channels` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_np_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_np_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '通知偏好表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for items
-- ----------------------------
DROP TABLE IF EXISTS `items`;
CREATE TABLE `items`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属房屋ID',
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '物品名称',
  `category_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '分类ID',
  `brand` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '品牌',
  `model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '型号/规格',
  `barcode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '条码',
  `unit_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '单位ID',
  `default_container_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '默认容器ID',
  `image_url` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '图片URL',
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '备注',
  `track_inventory` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否管理库存：0否1是',
  `track_expiry` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否管理过期：0否1是',
  `is_consumable` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否消耗品：0否1是',
  `low_stock_threshold` decimal(12, 3) NULL DEFAULT NULL COMMENT '低库存阈值',
  `expiry_warning_days` int NULL DEFAULT NULL COMMENT '过期提前提醒天数',
  `opened_expiry_days` int NULL DEFAULT NULL COMMENT '开封后可用天数',
  `default_shelf_life_days` int NULL DEFAULT NULL COMMENT '默认保质期天数',
  `attributes` json NULL COMMENT '扩展属性JSON',
  `current_quantity` decimal(12, 3) NOT NULL DEFAULT 0.000 COMMENT '当前总库存（冗余字段）',
  `created_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '创建人用户ID',
  `updated_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '更新人用户ID',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at` datetime(3) NULL DEFAULT NULL COMMENT '软删除时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_items_property`(`property_id` ASC) USING BTREE,
  INDEX `idx_items_property_category`(`property_id` ASC, `category_id` ASC) USING BTREE,
  INDEX `idx_items_property_name`(`property_id` ASC, `name` ASC) USING BTREE,
  INDEX `idx_items_barcode`(`property_id` ASC, `barcode` ASC) USING BTREE,
  INDEX `fk_items_category`(`category_id` ASC) USING BTREE,
  INDEX `fk_items_unit`(`unit_id` ASC) USING BTREE,
  INDEX `fk_items_default_container`(`default_container_id` ASC) USING BTREE,
  INDEX `fk_items_created_by`(`created_by` ASC) USING BTREE,
  INDEX `fk_items_updated_by`(`updated_by` ASC) USING BTREE,
  CONSTRAINT `fk_items_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_items_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_items_default_container` FOREIGN KEY (`default_container_id`) REFERENCES `containers` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_items_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_items_unit` FOREIGN KEY (`unit_id`) REFERENCES `units` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_items_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '物品主数据表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for item_batches
-- ----------------------------
DROP TABLE IF EXISTS `item_batches`;
CREATE TABLE `item_batches`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属房屋ID',
  `item_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '物品ID',
  `container_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '容器ID',
  `quantity` decimal(12, 3) NOT NULL DEFAULT 0.000 COMMENT '当前数量',
  `unit_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '单位ID',
  `production_date` date NULL DEFAULT NULL COMMENT '生产日期',
  `expiry_date` date NULL DEFAULT NULL COMMENT '过期日期',
  `opened_at` datetime(3) NULL DEFAULT NULL COMMENT '开封时间',
  `opened_expiry_date` date NULL DEFAULT NULL COMMENT '开封后过期日期',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '状态：active/consumed/expired/discarded/moved',
  `note` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '备注',
  `created_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '创建人用户ID',
  `updated_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '更新人用户ID',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_batches_property_item`(`property_id` ASC, `item_id` ASC) USING BTREE,
  INDEX `idx_batches_property_container`(`property_id` ASC, `container_id` ASC) USING BTREE,
  INDEX `idx_batches_expiry`(`expiry_date` ASC) USING BTREE,
  INDEX `idx_batches_opened_expiry`(`opened_expiry_date` ASC) USING BTREE,
  INDEX `idx_batches_status`(`property_id` ASC, `status` ASC) USING BTREE,
  INDEX `fk_batches_item`(`item_id` ASC) USING BTREE,
  INDEX `fk_batches_container`(`container_id` ASC) USING BTREE,
  INDEX `fk_batches_unit`(`unit_id` ASC) USING BTREE,
  INDEX `fk_batches_created_by`(`created_by` ASC) USING BTREE,
  INDEX `fk_batches_updated_by`(`updated_by` ASC) USING BTREE,
  CONSTRAINT `fk_batches_container` FOREIGN KEY (`container_id`) REFERENCES `containers` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_batches_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_batches_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_batches_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_batches_unit` FOREIGN KEY (`unit_id`) REFERENCES `units` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_batches_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '物品批次库存表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for item_tags
-- ----------------------------
DROP TABLE IF EXISTS `item_tags`;
CREATE TABLE `item_tags`  (
  `item_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '物品ID',
  `tag_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标签ID',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  PRIMARY KEY (`item_id`, `tag_id`) USING BTREE,
  INDEX `idx_item_tags_tag`(`tag_id` ASC) USING BTREE,
  CONSTRAINT `fk_item_tags_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_item_tags_tag` FOREIGN KEY (`tag_id`) REFERENCES `tags` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '物品标签关联表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for inventory_transactions
-- ----------------------------
DROP TABLE IF EXISTS `inventory_transactions`;
CREATE TABLE `inventory_transactions`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属房屋ID',
  `item_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '物品ID',
  `batch_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '批次ID',
  `container_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '容器ID',
  `type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '类型：in/out/consume/move/adjust/discard/return',
  `quantity_delta` decimal(12, 3) NOT NULL COMMENT '数量变化',
  `quantity_after` decimal(12, 3) NULL DEFAULT NULL COMMENT '变化后数量',
  `unit_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '单位ID',
  `reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '原因',
  `created_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '创建人用户ID',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_transactions_property_item`(`property_id` ASC, `item_id` ASC) USING BTREE,
  INDEX `idx_transactions_property_batch`(`property_id` ASC, `batch_id` ASC) USING BTREE,
  INDEX `idx_transactions_created_at`(`created_at` ASC) USING BTREE,
  INDEX `fk_transactions_item`(`item_id` ASC) USING BTREE,
  INDEX `fk_transactions_batch`(`batch_id` ASC) USING BTREE,
  INDEX `fk_transactions_container`(`container_id` ASC) USING BTREE,
  INDEX `fk_transactions_unit`(`unit_id` ASC) USING BTREE,
  INDEX `fk_transactions_created_by`(`created_by` ASC) USING BTREE,
  CONSTRAINT `fk_transactions_batch` FOREIGN KEY (`batch_id`) REFERENCES `item_batches` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_transactions_container` FOREIGN KEY (`container_id`) REFERENCES `containers` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_transactions_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_transactions_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_transactions_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_transactions_unit` FOREIGN KEY (`unit_id`) REFERENCES `units` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '库存流水表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for reminders
-- ----------------------------
DROP TABLE IF EXISTS `reminders`;
CREATE TABLE `reminders`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属房屋ID',
  `type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '类型：expiry/opened_expiry/low_stock/custom',
  `item_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '物品ID',
  `batch_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '批次ID',
  `container_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '容器ID',
  `trigger_at` datetime(3) NOT NULL COMMENT '触发时间',
  `threshold` decimal(12, 3) NULL DEFAULT NULL COMMENT '阈值',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '状态：pending/done/snoozed/dismissed',
  `snooze_until` datetime(3) NULL DEFAULT NULL COMMENT '稍后提醒时间',
  `last_notified_at` datetime(3) NULL DEFAULT NULL COMMENT '上次通知时间',
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '提醒内容',
  `dedupe_key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '去重键',
  `created_by` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '创建人用户ID',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_reminders_dedupe`(`property_id` ASC, `dedupe_key` ASC) USING BTREE,
  INDEX `idx_reminders_property_status_trigger`(`property_id` ASC, `status` ASC, `trigger_at` ASC) USING BTREE,
  INDEX `idx_reminders_item`(`item_id` ASC) USING BTREE,
  INDEX `idx_reminders_batch`(`batch_id` ASC) USING BTREE,
  INDEX `fk_reminders_container`(`container_id` ASC) USING BTREE,
  INDEX `fk_reminders_created_by`(`created_by` ASC) USING BTREE,
  CONSTRAINT `fk_reminders_batch` FOREIGN KEY (`batch_id`) REFERENCES `item_batches` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_reminders_container` FOREIGN KEY (`container_id`) REFERENCES `containers` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_reminders_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_reminders_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_reminders_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '提醒表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for notifications
-- ----------------------------
DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `property_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '房屋ID（可空）',
  `user_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户ID',
  `reminder_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '提醒ID',
  `channel_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '渠道ID',
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '标题',
  `body` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '内容',
  `payload` json NULL COMMENT '负载JSON',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '状态：pending/sent/failed/read',
  `sent_at` datetime(3) NULL DEFAULT NULL COMMENT '发送时间',
  `read_at` datetime(3) NULL DEFAULT NULL COMMENT '阅读时间',
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '错误信息',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_notifications_user_status`(`user_id` ASC, `status` ASC) USING BTREE,
  INDEX `idx_notifications_property`(`property_id` ASC) USING BTREE,
  INDEX `idx_notifications_created_at`(`created_at` ASC) USING BTREE,
  INDEX `fk_notifications_reminder`(`reminder_id` ASC) USING BTREE,
  INDEX `fk_notifications_channel`(`channel_id` ASC) USING BTREE,
  CONSTRAINT `fk_notifications_channel` FOREIGN KEY (`channel_id`) REFERENCES `notification_channels` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_notifications_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_notifications_reminder` FOREIGN KEY (`reminder_id`) REFERENCES `reminders` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_notifications_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '通知记录表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for reminder_recipients
-- ----------------------------
DROP TABLE IF EXISTS `reminder_recipients`;
CREATE TABLE `reminder_recipients`  (
  `id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (REPLACE(uuid(), '-', '')) COMMENT '主键',
  `reminder_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '提醒ID',
  `user_id` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户ID',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '状态：pending/read/done/snoozed/dismissed',
  `read_at` datetime(3) NULL DEFAULT NULL COMMENT '阅读时间',
  `done_at` datetime(3) NULL DEFAULT NULL COMMENT '完成时间',
  `snoozed_until` datetime(3) NULL DEFAULT NULL COMMENT '稍后提醒时间',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_reminder_recipients`(`reminder_id` ASC, `user_id` ASC) USING BTREE,
  INDEX `idx_reminder_recipients_user`(`user_id` ASC, `status` ASC) USING BTREE,
  CONSTRAINT `fk_rr_reminder` FOREIGN KEY (`reminder_id`) REFERENCES `reminders` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_rr_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '提醒接收人表' ROW_FORMAT = Dynamic;

-- ----------------------------

SET FOREIGN_KEY_CHECKS = 1;