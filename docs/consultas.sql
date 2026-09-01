select * from usua_usuarios;
select * from usua_rol_perfiles;				-- ya no es necesaria
select * from usua_usuarios_groups;				-- ya no es necesaria
select * from usua_usuarios_user_permissions;  	-- ya no es necesaria

select * from auth_group;
select * from auth_group_permissions;
select * from auth_permission;

-- permisos por grupos
select gp.group_id, g.name, gp.permission_id, p.codename, p.name
from auth_group g
join auth_group_permissions gp on gp.group_id = g.id
join auth_permission p on p.id = gp.permission_id
where g.id=4;

