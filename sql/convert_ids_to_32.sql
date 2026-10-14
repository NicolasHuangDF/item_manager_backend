-- ============================================================
-- 将当前数据库所有 UUID 字段统一转换为：
--   32 位、无连字符、全大写
--
-- 使用前请先选择数据库：
--   USE item_manager;
-- 然后执行本脚本。
-- ============================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS `convert_ids_to_32` $$

CREATE PROCEDURE `convert_ids_to_32`()
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE table_name_value VARCHAR(128);
    DECLARE column_name_value VARCHAR(128);

    DECLARE cur CURSOR FOR
        SELECT TABLE_NAME, COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND DATA_TYPE IN ('char', 'varchar')
          AND CHARACTER_MAXIMUM_LENGTH >= 32
          AND (
                COLUMN_NAME = 'id'
                OR RIGHT(COLUMN_NAME, 3) = '_id'
                OR RIGHT(COLUMN_NAME, 3) = '_by'
          )
        ORDER BY TABLE_NAME, COLUMN_NAME;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    SET FOREIGN_KEY_CHECKS = 0;

    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO table_name_value, column_name_value;
        IF done THEN
            LEAVE read_loop;
        END IF;

        SET @update_sql = CONCAT(
            'UPDATE `', table_name_value, '` ',
            'SET `', column_name_value, '` = ',
            'UPPER(REPLACE(`', column_name_value,
            '`, CHAR(45), SPACE(0))) ',
            'WHERE `', column_name_value, '` IS NOT NULL'
        );
        PREPARE stmt FROM @update_sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END LOOP;
    CLOSE cur;

    SET FOREIGN_KEY_CHECKS = 1;
END $$

DELIMITER ;

CALL `convert_ids_to_32`();
DROP PROCEDURE `convert_ids_to_32`;
