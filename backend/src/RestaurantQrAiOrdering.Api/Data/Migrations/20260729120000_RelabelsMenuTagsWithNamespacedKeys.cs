using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations;

/// <summary>
/// Gán nhãn lại thực đơn theo khóa có không gian tên, và hợp nhất hai nguồn nhãn.
///
/// Trước migration này, cơ sở dữ liệu và tệp `backend/data/menu-dataset.json` mang hai
/// bộ nhãn khác nhau cho cùng 91 món: cơ sở dữ liệu 1,7 nhãn/món, tệp JSON 15 nhãn/món.
/// Trợ lý AI đọc tệp JSON, còn khách xem thực đơn qua `/api/menu` thấy nhãn từ cơ sở dữ
/// liệu — nên AI suy luận trên dữ liệu dày gấp gần chín lần thứ khách thật nhìn thấy.
///
/// Nhãn cũng đổi dạng: từ tiếng Việt trần (`toi`, `ca`, `nam`) sang khóa có không gian
/// tên (`meal:dinner`, `ingredient:fish`, `ingredient:mushroom`). Dạng cũ trùng với từ
/// thông thường sau khi rút dấu, và đó là gốc của bảy lỗi trong bản AI trước
/// (`cua`/`của`, `chay`/`chạy`, `muc`/`mức`...). Khách không bao giờ gõ `meal:dinner`,
/// nên cả lớp lỗi đó biến mất về mặt cấu trúc.
///
/// Nhãn hiển thị cho khách không đổi: giao diện tra `backend/data/menu-tags.json` và
/// nhận cả khóa mới lẫn tên cũ, nên "Tối", "Cá", "Bình dân" vẫn hiện như trước.
///
/// Sinh bởi `ai/scripts/build_tag_migration.py` — sửa nhãn thì chạy lại script, đừng sửa
/// tay tệp này.
/// </summary>
[DbContext(typeof(RestaurantDbContext))]
[Migration("20260729120000_RelabelsMenuTagsWithNamespacedKeys")]
public partial class RelabelsMenuTagsWithNamespacedKeys : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        // Cập nhật theo mã món, không theo tên: tên có thể đổi, mã thì không.
        migrationBuilder.Sql(
            """
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'health:light', 'health:low_fat', 'ingredient:pork', 'meal:breakfast', 'method:steamed', 'occasion:everyday', 'party:solo', 'price:budget', 'region:hanoi', 'region:north', 'season:all_year', 'serving:takeaway', 'spice:none']::text[]
                WHERE id = 'm_004';
            UPDATE menu_items SET tags = ARRAY['allergen:gluten', 'audience:child', 'flavour:rich', 'ingredient:pork', 'meal:breakfast', 'meal:late_night', 'meal:lunch', 'method:grilled', 'occasion:everyday', 'party:solo', 'price:budget', 'region:saigon', 'region:south', 'season:all_year', 'serving:takeaway', 'spice:mild']::text[]
                WHERE id = 'm_006';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'audience:child', 'flavour:sweet', 'ingredient:pork', 'ingredient:shrimp', 'meal:dinner', 'meal:lunch', 'method:fried', 'party:family', 'party:share', 'party:two_three', 'price:mid', 'region:mekong', 'region:south', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_003';
            UPDATE menu_items SET tags = ARRAY['allergen:peanut', 'allergen:seafood', 'audience:child', 'health:healthy', 'health:light', 'health:low_calorie', 'health:low_fat', 'ingredient:pork', 'ingredient:shrimp', 'meal:lunch', 'method:rolled', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'promo:popular', 'promo:signature', 'region:south', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_001';
            UPDATE menu_items SET tags = ARRAY['allergen:peanut', 'allergen:seafood', 'flavour:sour', 'health:healthy', 'health:low_calorie', 'ingredient:shrimp', 'meal:dinner', 'meal:lunch', 'method:rolled', 'party:friends', 'party:share', 'price:mid', 'region:south', 'season:cooling', 'season:hot_season', 'spice:mild']::text[]
                WHERE id = 'm_005';
            UPDATE menu_items SET tags = ARRAY['allergen:gluten', 'allergen:seafood', 'audience:child', 'flavour:rich', 'ingredient:pork', 'ingredient:shrimp', 'meal:dinner', 'meal:lunch', 'method:fried', 'occasion:banquet', 'party:family', 'party:friends', 'party:share', 'price:budget', 'region:hanoi', 'region:north', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_002';
            UPDATE menu_items SET tags = ARRAY['allergen:egg', 'allergen:seafood', 'audience:child', 'audience:elderly', 'flavour:fatty', 'health:light', 'health:low_fat', 'ingredient:crab', 'ingredient:mushroom', 'meal:dinner', 'method:simmered', 'occasion:everyday', 'party:family', 'party:solo', 'price:mid', 'region:south', 'season:cold_season', 'serving:hot', 'spice:none']::text[]
                WHERE id = 'm_007';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'flavour:rich', 'flavour:salty', 'health:high_protein', 'ingredient:beef', 'ingredient:pork', 'meal:breakfast', 'meal:lunch', 'method:simmered', 'occasion:everyday', 'party:friends', 'party:solo', 'price:mid', 'region:central', 'region:hue', 'season:all_year', 'spice:hot']::text[]
                WHERE id = 'm_010';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'flavour:smoky', 'health:high_protein', 'ingredient:pork', 'meal:lunch', 'method:grilled', 'occasion:business', 'occasion:everyday', 'party:family', 'party:friends', 'party:solo', 'price:budget', 'region:hanoi', 'region:north', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_011';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'flavour:rich', 'flavour:salty', 'ingredient:fish', 'ingredient:pork', 'ingredient:shrimp', 'ingredient:squid', 'meal:dinner', 'meal:lunch', 'method:simmered', 'party:friends', 'party:solo', 'price:mid', 'region:mekong', 'region:south', 'season:all_year', 'spice:mild']::text[]
                WHERE id = 'm_013';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'audience:child', 'audience:elderly', 'flavour:sour', 'health:light', 'ingredient:crab', 'ingredient:pork', 'meal:breakfast', 'meal:lunch', 'method:simmered', 'occasion:everyday', 'party:solo', 'price:budget', 'region:north', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_012';
            UPDATE menu_items SET tags = ARRAY['allergen:gluten', 'allergen:seafood', 'flavour:rich', 'flavour:salty', 'ingredient:pork', 'ingredient:tofu', 'meal:dinner', 'meal:lunch', 'method:boiled', 'method:fried', 'occasion:drinking', 'party:friends', 'party:share', 'party:two_three', 'price:mid', 'region:hanoi', 'region:north', 'season:all_year', 'spice:medium']::text[]
                WHERE id = 'm_014';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'health:high_protein', 'health:light', 'ingredient:beef', 'meal:breakfast', 'meal:lunch', 'method:simmered', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'promo:signature', 'region:hanoi', 'region:north', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_008';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'health:light', 'health:low_fat', 'ingredient:chicken', 'meal:breakfast', 'method:simmered', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:hanoi', 'region:north', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_009';
            UPDATE menu_items SET tags = ARRAY['flavour:rich', 'health:high_protein', 'ingredient:beef', 'meal:dinner', 'meal:lunch', 'method:stir_fried', 'occasion:business', 'occasion:everyday', 'party:solo', 'price:mid', 'region:saigon', 'region:south', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_021';
            UPDATE menu_items SET tags = ARRAY['allergen:egg', 'allergen:seafood', 'audience:child', 'flavour:rich', 'ingredient:pork', 'ingredient:shrimp', 'meal:dinner', 'meal:lunch', 'method:fried', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:saigon', 'region:south', 'season:all_year', 'serving:takeaway', 'spice:none']::text[]
                WHERE id = 'm_019';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'audience:elderly', 'flavour:rich', 'flavour:salty', 'flavour:sweet', 'health:high_protein', 'ingredient:fish', 'meal:dinner', 'meal:lunch', 'method:braised', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:south', 'season:all_year', 'spice:mild']::text[]
                WHERE id = 'm_018';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'health:high_protein', 'health:light', 'ingredient:chicken', 'meal:breakfast', 'meal:lunch', 'method:boiled', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:central', 'region:danang', 'region:hoian', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_016';
            UPDATE menu_items SET tags = ARRAY['allergen:peanut', 'allergen:seafood', 'flavour:fatty', 'flavour:rich', 'flavour:salty', 'flavour:sour', 'ingredient:vegetable', 'meal:breakfast', 'meal:lunch', 'method:stir_fried', 'occasion:everyday', 'party:friends', 'party:solo', 'price:budget', 'region:central', 'region:hue', 'season:all_year', 'spice:medium']::text[]
                WHERE id = 'm_020';
            UPDATE menu_items SET tags = ARRAY['allergen:egg', 'flavour:rich', 'flavour:smoky', 'flavour:sweet', 'health:high_protein', 'ingredient:pork', 'meal:dinner', 'meal:lunch', 'method:grilled', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:saigon', 'region:south', 'season:all_year', 'spice:mild']::text[]
                WHERE id = 'm_017';
            UPDATE menu_items SET tags = ARRAY['allergen:egg', 'audience:child', 'flavour:rich', 'flavour:sweet', 'health:high_protein', 'ingredient:pork', 'meal:breakfast', 'meal:lunch', 'method:grilled', 'method:steamed', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'promo:popular', 'region:saigon', 'region:south', 'season:all_year', 'serving:takeaway', 'spice:none']::text[]
                WHERE id = 'm_015';
            UPDATE menu_items SET tags = ARRAY['allergen:gluten', 'allergen:seafood', 'flavour:sour', 'flavour:sweet', 'health:high_protein', 'ingredient:crab', 'meal:dinner', 'method:roasted', 'occasion:banquet', 'occasion:business', 'party:friends', 'party:share', 'party:two_three', 'price:high', 'region:saigon', 'region:south', 'season:all_year', 'serving:preorder', 'spice:none']::text[]
                WHERE id = 'm_025';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'flavour:smoky', 'flavour:sweet', 'health:high_protein', 'health:low_fat', 'ingredient:fish', 'meal:dinner', 'method:grilled', 'occasion:drinking', 'party:friends', 'party:share', 'party:two_three', 'price:mid', 'region:mekong', 'region:south', 'season:all_year', 'serving:preorder', 'spice:mild']::text[]
                WHERE id = 'm_023';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'flavour:rich', 'health:high_protein', 'ingredient:squid', 'meal:dinner', 'method:stir_fried', 'occasion:drinking', 'party:friends', 'party:solo', 'price:mid', 'region:south', 'season:all_year', 'spice:hot']::text[]
                WHERE id = 'm_026';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'health:healthy', 'health:light', 'health:low_calorie', 'ingredient:vegetable', 'meal:dinner', 'method:steamed', 'occasion:drinking', 'party:friends', 'party:share', 'price:mid', 'region:south', 'season:all_year', 'spice:mild']::text[]
                WHERE id = 'm_027';
            UPDATE menu_items SET tags = ARRAY['allergen:peanut', 'allergen:seafood', 'flavour:fatty', 'flavour:sweet', 'health:high_protein', 'ingredient:shrimp', 'meal:dinner', 'method:grilled', 'occasion:banquet', 'occasion:birthday', 'occasion:business', 'occasion:date', 'party:two_three', 'price:premium', 'region:central', 'season:all_year', 'serving:preorder', 'spice:none']::text[]
                WHERE id = 'm_022';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'flavour:rich', 'flavour:salty', 'health:high_protein', 'ingredient:shrimp', 'meal:dinner', 'method:roasted', 'occasion:drinking', 'party:friends', 'party:share', 'price:mid', 'region:south', 'season:all_year', 'spice:mild']::text[]
                WHERE id = 'm_024';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'allergen:seafood', 'flavour:fatty', 'flavour:sweet', 'health:high_protein', 'ingredient:vegetable', 'meal:dinner', 'method:roasted', 'occasion:drinking', 'party:friends', 'party:share', 'price:mid', 'region:central', 'season:all_year', 'serving:preorder', 'spice:none']::text[]
                WHERE id = 'm_028';
            UPDATE menu_items SET tags = ARRAY['flavour:sour', 'health:high_protein', 'health:light', 'ingredient:beef', 'meal:dinner', 'method:simmered', 'occasion:business', 'party:family', 'party:share', 'party:three_five', 'party:two_three', 'price:high', 'region:south', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_030';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'audience:child', 'flavour:sour', 'health:high_protein', 'health:light', 'ingredient:fish', 'meal:dinner', 'method:simmered', 'party:family', 'party:share', 'party:three_five', 'party:two_three', 'price:high', 'region:north', 'season:cold_season', 'spice:none']::text[]
                WHERE id = 'm_029';
            UPDATE menu_items SET tags = ARRAY['flavour:fatty', 'flavour:rich', 'health:high_protein', 'ingredient:beef', 'ingredient:mushroom', 'meal:dinner', 'method:simmered', 'method:stewed', 'occasion:drinking', 'party:friends', 'party:share', 'party:three_five', 'price:high', 'season:cold_season', 'serving:preorder', 'spice:mild']::text[]
                WHERE id = 'm_034';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'flavour:sweet', 'health:high_protein', 'health:light', 'ingredient:chicken', 'ingredient:mushroom', 'meal:dinner', 'method:simmered', 'party:family', 'party:share', 'party:three_five', 'price:mid', 'region:highlands', 'season:cold_season', 'serving:preorder', 'spice:none']::text[]
                WHERE id = 'm_032';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'flavour:rich', 'flavour:sour', 'health:high_protein', 'ingredient:fish', 'ingredient:shrimp', 'ingredient:squid', 'meal:dinner', 'method:simmered', 'occasion:banquet', 'party:friends', 'party:share', 'party:three_five', 'price:high', 'region:south', 'season:all_year', 'serving:preorder', 'spice:hot']::text[]
                WHERE id = 'm_033';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'flavour:rich', 'flavour:salty', 'ingredient:fish', 'ingredient:pork', 'ingredient:shrimp', 'meal:dinner', 'method:simmered', 'occasion:drinking', 'party:friends', 'party:share', 'party:three_five', 'price:high', 'region:mekong', 'region:south', 'season:all_year', 'spice:medium']::text[]
                WHERE id = 'm_035';
            UPDATE menu_items SET tags = ARRAY['diet:vegan', 'diet:vegetarian', 'health:healthy', 'health:light', 'health:low_calorie', 'health:no_msg', 'ingredient:mushroom', 'ingredient:tofu', 'ingredient:vegetable', 'meal:dinner', 'method:simmered', 'party:family', 'party:share', 'party:two_three', 'price:mid', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_031';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'flavour:rich', 'flavour:salty', 'flavour:sweet', 'health:high_protein', 'ingredient:chicken', 'meal:dinner', 'method:fried', 'occasion:drinking', 'occasion:everyday', 'party:friends', 'party:share', 'party:solo', 'price:mid', 'region:south', 'season:all_year', 'spice:mild']::text[]
                WHERE id = 'm_038';
            UPDATE menu_items SET tags = ARRAY['audience:elderly', 'health:healthy', 'health:high_protein', 'health:light', 'health:low_fat', 'ingredient:chicken', 'meal:dinner', 'method:steamed', 'occasion:banquet', 'occasion:business', 'party:family', 'party:share', 'party:three_five', 'price:high', 'season:all_year', 'serving:preorder', 'spice:none']::text[]
                WHERE id = 'm_037';
            UPDATE menu_items SET tags = ARRAY['flavour:rich', 'flavour:salty', 'flavour:smoky', 'health:high_protein', 'ingredient:chicken', 'meal:dinner', 'method:grilled', 'occasion:drinking', 'party:friends', 'party:share', 'party:two_three', 'price:mid', 'season:all_year', 'serving:preorder', 'spice:medium']::text[]
                WHERE id = 'm_040';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'flavour:smoky', 'flavour:sweet', 'health:high_protein', 'ingredient:chicken', 'meal:dinner', 'method:grilled', 'occasion:everyday', 'party:family', 'party:share', 'party:solo', 'price:mid', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_036';
            UPDATE menu_items SET tags = ARRAY['flavour:rich', 'flavour:smoky', 'flavour:sweet', 'health:high_protein', 'ingredient:chicken', 'meal:dinner', 'method:grilled', 'occasion:banquet', 'occasion:birthday', 'occasion:business', 'party:family', 'party:share', 'party:three_five', 'price:high', 'season:all_year', 'serving:preorder', 'spice:none']::text[]
                WHERE id = 'm_042';
            UPDATE menu_items SET tags = ARRAY['audience:elderly', 'flavour:fatty', 'flavour:sweet', 'health:healthy', 'health:light', 'ingredient:chicken', 'ingredient:mushroom', 'meal:dinner', 'method:stewed', 'party:solo', 'price:high', 'season:cold_season', 'serving:preorder', 'spice:none']::text[]
                WHERE id = 'm_041';
            UPDATE menu_items SET tags = ARRAY['flavour:rich', 'health:high_protein', 'ingredient:chicken', 'meal:dinner', 'meal:lunch', 'method:stir_fried', 'occasion:everyday', 'party:family', 'party:solo', 'price:mid', 'season:all_year', 'spice:medium']::text[]
                WHERE id = 'm_039';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'health:healthy', 'health:light', 'health:low_calorie', 'health:low_fat', 'ingredient:pork', 'meal:dinner', 'method:boiled', 'method:rolled', 'party:friends', 'party:share', 'party:two_three', 'price:mid', 'region:central', 'region:danang', 'season:hot_season', 'spice:mild']::text[]
                WHERE id = 'm_047';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'flavour:rich', 'flavour:smoky', 'health:high_protein', 'ingredient:beef', 'meal:dinner', 'method:grilled', 'occasion:banquet', 'occasion:drinking', 'party:friends', 'party:share', 'party:three_five', 'price:high', 'region:central', 'season:all_year', 'serving:preorder', 'spice:mild']::text[]
                WHERE id = 'm_045';
            UPDATE menu_items SET tags = ARRAY['allergen:gluten', 'flavour:rich', 'ingredient:pork', 'meal:lunch', 'method:simmered', 'occasion:business', 'occasion:everyday', 'party:solo', 'price:mid', 'region:central', 'region:danang', 'region:hoian', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_044';
            UPDATE menu_items SET tags = ARRAY['allergen:gluten', 'audience:child', 'audience:elderly', 'flavour:fatty', 'health:light', 'ingredient:pork', 'meal:breakfast', 'meal:late_night', 'method:simmered', 'occasion:everyday', 'party:solo', 'price:budget', 'region:saigon', 'region:south', 'season:cold_season', 'spice:none']::text[]
                WHERE id = 'm_048';
            UPDATE menu_items SET tags = ARRAY['allergen:seafood', 'audience:child', 'audience:elderly', 'health:light', 'ingredient:pork', 'ingredient:shrimp', 'meal:breakfast', 'meal:late_night', 'method:simmered', 'occasion:everyday', 'party:solo', 'price:budget', 'region:saigon', 'region:south', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_046';
            UPDATE menu_items SET tags = ARRAY['allergen:egg', 'allergen:peanut', 'allergen:seafood', 'flavour:rich', 'health:high_protein', 'ingredient:pork', 'ingredient:shrimp', 'meal:breakfast', 'meal:lunch', 'method:simmered', 'occasion:everyday', 'party:friends', 'party:solo', 'price:budget', 'region:central', 'region:danang', 'season:all_year', 'spice:mild']::text[]
                WHERE id = 'm_043';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'flavour:fatty', 'flavour:sweet', 'health:high_protein', 'ingredient:chicken', 'meal:breakfast', 'method:steamed', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:hanoi', 'region:north', 'season:all_year', 'serving:takeaway', 'spice:none']::text[]
                WHERE id = 'm_049';
            UPDATE menu_items SET tags = ARRAY['diet:vegan', 'diet:vegetarian', 'flavour:rich', 'flavour:salty', 'ingredient:mushroom', 'ingredient:tofu', 'ingredient:vegetable', 'meal:lunch', 'method:simmered', 'occasion:everyday', 'party:solo', 'price:budget', 'region:central', 'region:hue', 'season:all_year', 'spice:medium']::text[]
                WHERE id = 'm_056';
            UPDATE menu_items SET tags = ARRAY['audience:elderly', 'diet:vegan', 'diet:vegetarian', 'health:healthy', 'health:light', 'health:low_calorie', 'health:no_msg', 'ingredient:mushroom', 'ingredient:tofu', 'ingredient:vegetable', 'meal:dinner', 'meal:lunch', 'method:simmered', 'party:solo', 'price:budget', 'season:cooling', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_053';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'diet:vegan', 'diet:vegetarian', 'health:healthy', 'health:light', 'health:no_msg', 'ingredient:mushroom', 'ingredient:tofu', 'ingredient:vegetable', 'meal:dinner', 'meal:lunch', 'method:fried', 'occasion:everyday', 'party:solo', 'price:budget', 'season:all_year', 'serving:takeaway', 'spice:none']::text[]
                WHERE id = 'm_051';
            UPDATE menu_items SET tags = ARRAY['allergen:peanut', 'audience:child', 'audience:elderly', 'diet:vegan', 'diet:vegetarian', 'health:healthy', 'health:light', 'health:low_calorie', 'health:low_fat', 'ingredient:tofu', 'ingredient:vegetable', 'meal:lunch', 'method:rolled', 'occasion:everyday', 'party:solo', 'price:budget', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_052';
            UPDATE menu_items SET tags = ARRAY['allergen:peanut', 'diet:vegan', 'diet:vegetarian', 'flavour:rich', 'ingredient:mushroom', 'ingredient:tofu', 'ingredient:vegetable', 'meal:lunch', 'method:simmered', 'occasion:everyday', 'party:solo', 'price:budget', 'region:central', 'season:all_year', 'spice:mild']::text[]
                WHERE id = 'm_055';
            UPDATE menu_items SET tags = ARRAY['audience:elderly', 'diet:vegan', 'diet:vegetarian', 'health:healthy', 'health:light', 'health:low_calorie', 'health:no_msg', 'ingredient:mushroom', 'ingredient:tofu', 'ingredient:vegetable', 'meal:breakfast', 'meal:lunch', 'method:simmered', 'occasion:everyday', 'party:solo', 'price:budget', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_050';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'diet:vegan', 'diet:vegetarian', 'flavour:sour', 'flavour:sweet', 'health:high_protein', 'ingredient:tofu', 'ingredient:vegetable', 'meal:dinner', 'meal:lunch', 'method:fried', 'occasion:everyday', 'party:solo', 'price:budget', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_054';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'audience:child', 'flavour:fatty', 'flavour:sweet', 'health:light', 'meal:breakfast', 'occasion:everyday', 'party:solo', 'price:budget', 'region:saigon', 'region:south', 'season:all_year', 'serving:takeaway', 'spice:none']::text[]
                WHERE id = 'm_059';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'flavour:fatty', 'flavour:sweet', 'meal:breakfast', 'meal:lunch', 'occasion:everyday', 'party:friends', 'party:solo', 'price:budget', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_063';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'flavour:fatty', 'flavour:rich', 'flavour:sweet', 'meal:breakfast', 'meal:lunch', 'occasion:everyday', 'party:friends', 'party:solo', 'price:budget', 'promo:popular', 'season:all_year', 'serving:takeaway', 'spice:none']::text[]
                WHERE id = 'm_057';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'allergen:egg', 'flavour:fatty', 'flavour:sweet', 'meal:breakfast', 'occasion:business', 'occasion:everyday', 'party:solo', 'price:budget', 'region:hanoi', 'region:north', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_058';
            UPDATE menu_items SET tags = ARRAY['audience:elderly', 'health:healthy', 'health:light', 'health:low_calorie', 'meal:dinner', 'occasion:business', 'party:solo', 'price:mid', 'region:hanoi', 'region:north', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_061';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'audience:child', 'flavour:fatty', 'flavour:sweet', 'meal:dinner', 'meal:lunch', 'occasion:everyday', 'party:friends', 'party:solo', 'price:budget', 'season:all_year', 'serving:takeaway', 'spice:none']::text[]
                WHERE id = 'm_062';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'flavour:sour', 'flavour:sweet', 'health:healthy', 'health:light', 'meal:breakfast', 'meal:dinner', 'meal:lunch', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'season:cooling', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_060';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'flavour:sweet', 'health:light', 'meal:breakfast', 'meal:lunch', 'occasion:everyday', 'party:solo', 'price:budget', 'region:saigon', 'region:south', 'season:cooling', 'season:hot_season', 'serving:takeaway', 'spice:none']::text[]
                WHERE id = 'm_070';
            UPDATE menu_items SET tags = ARRAY['audience:elderly', 'health:healthy', 'health:light', 'health:low_calorie', 'ingredient:vegetable', 'meal:dinner', 'meal:lunch', 'occasion:everyday', 'party:solo', 'price:budget', 'region:south', 'season:cooling', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_068';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'flavour:sour', 'flavour:sweet', 'health:healthy', 'health:light', 'health:low_calorie', 'meal:breakfast', 'meal:lunch', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'season:all_year', 'season:cooling', 'spice:none']::text[]
                WHERE id = 'm_064';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'flavour:sweet', 'health:healthy', 'health:light', 'health:low_calorie', 'meal:dinner', 'meal:lunch', 'occasion:everyday', 'party:solo', 'price:budget', 'season:cooling', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_066';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'audience:child', 'flavour:fatty', 'flavour:sweet', 'health:healthy', 'health:high_protein', 'meal:breakfast', 'meal:lunch', 'occasion:everyday', 'party:solo', 'price:budget', 'region:highlands', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_065';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'audience:child', 'flavour:sour', 'flavour:sweet', 'health:healthy', 'health:low_calorie', 'meal:dinner', 'meal:lunch', 'occasion:everyday', 'party:solo', 'price:budget', 'region:highlands', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_069';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'audience:child', 'flavour:sweet', 'health:healthy', 'meal:dinner', 'meal:lunch', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:south', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_067';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'allergen:gluten', 'audience:child', 'flavour:fatty', 'flavour:sweet', 'meal:dinner', 'method:grilled', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:south', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_076';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'allergen:egg', 'audience:child', 'audience:elderly', 'flavour:fatty', 'flavour:sweet', 'meal:dinner', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_072';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'flavour:fatty', 'flavour:sweet', 'meal:dinner', 'occasion:everyday', 'party:solo', 'price:budget', 'region:south', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_073';
            UPDATE menu_items SET tags = ARRAY['allergen:dairy', 'audience:child', 'flavour:sweet', 'health:light', 'meal:dinner', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:north', 'season:cooling', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_071';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'diet:vegan', 'diet:vegetarian', 'flavour:fatty', 'flavour:sweet', 'meal:dinner', 'occasion:everyday', 'party:solo', 'price:budget', 'season:cold_season', 'spice:none']::text[]
                WHERE id = 'm_075';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'diet:vegan', 'diet:vegetarian', 'flavour:sweet', 'health:light', 'meal:dinner', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:south', 'season:cooling', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_074';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'diet:vegan', 'diet:vegetarian', 'flavour:fatty', 'flavour:sweet', 'meal:dinner', 'occasion:everyday', 'party:family', 'party:solo', 'price:budget', 'region:south', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_077';
            UPDATE menu_items SET tags = ARRAY['audience:elderly', 'diet:vegan', 'diet:vegetarian', 'health:healthy', 'health:light', 'health:low_calorie', 'meal:dinner', 'party:solo', 'price:budget', 'region:mekong', 'region:south', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_082';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'diet:vegan', 'diet:vegetarian', 'flavour:sweet', 'health:healthy', 'health:light', 'health:low_calorie', 'meal:dinner', 'occasion:everyday', 'party:solo', 'price:budget', 'season:cooling', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_081';
            UPDATE menu_items SET tags = ARRAY['flavour:fatty', 'flavour:sweet', 'meal:dinner', 'party:friends', 'party:solo', 'price:mid', 'region:south', 'season:hot_season', 'serving:takeaway', 'spice:none']::text[]
                WHERE id = 'm_080';
            UPDATE menu_items SET tags = ARRAY['audience:elderly', 'diet:vegan', 'diet:vegetarian', 'flavour:sweet', 'health:healthy', 'health:light', 'health:low_calorie', 'meal:dinner', 'occasion:everyday', 'party:solo', 'price:budget', 'region:south', 'season:all_year', 'season:cooling', 'spice:none']::text[]
                WHERE id = 'm_083';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'diet:vegan', 'diet:vegetarian', 'flavour:sweet', 'health:healthy', 'health:low_calorie', 'meal:dinner', 'party:family', 'party:solo', 'price:budget', 'region:south', 'season:hot_season', 'spice:none']::text[]
                WHERE id = 'm_079';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'audience:elderly', 'diet:vegan', 'diet:vegetarian', 'flavour:sweet', 'health:healthy', 'health:light', 'health:low_calorie', 'meal:dinner', 'occasion:everyday', 'party:solo', 'price:budget', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_084';
            UPDATE menu_items SET tags = ARRAY['audience:child', 'diet:vegan', 'diet:vegetarian', 'flavour:sweet', 'health:healthy', 'health:light', 'health:low_calorie', 'meal:dinner', 'occasion:banquet', 'party:family', 'party:friends', 'party:share', 'party:two_three', 'price:mid', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_078';
            UPDATE menu_items SET tags = ARRAY['flavour:rich', 'meal:dinner', 'occasion:drinking', 'party:family', 'party:friends', 'party:solo', 'price:budget', 'region:saigon', 'region:south', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_085';
            UPDATE menu_items SET tags = ARRAY['flavour:rich', 'meal:dinner', 'occasion:drinking', 'party:friends', 'party:solo', 'price:budget', 'region:hanoi', 'region:north', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_086';
            UPDATE menu_items SET tags = ARRAY['health:light', 'meal:dinner', 'occasion:date', 'occasion:drinking', 'party:friends', 'party:solo', 'price:budget', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_087';
            UPDATE menu_items SET tags = ARRAY['health:light', 'meal:dinner', 'meal:late_night', 'occasion:drinking', 'party:friends', 'party:solo', 'price:budget', 'region:hanoi', 'region:north', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_088';
            UPDATE menu_items SET tags = ARRAY['flavour:rich', 'flavour:sweet', 'meal:dinner', 'occasion:banquet', 'occasion:business', 'occasion:drinking', 'party:solo', 'price:mid', 'region:north', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_089';
            UPDATE menu_items SET tags = ARRAY['flavour:sour', 'flavour:sweet', 'health:light', 'meal:dinner', 'occasion:banquet', 'occasion:business', 'occasion:date', 'occasion:drinking', 'party:solo', 'price:mid', 'region:hanoi', 'region:north', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_090';
            UPDATE menu_items SET tags = ARRAY['flavour:sour', 'flavour:sweet', 'health:light', 'meal:dinner', 'occasion:banquet', 'occasion:birthday', 'occasion:date', 'party:friends', 'party:solo', 'price:mid', 'season:all_year', 'spice:none']::text[]
                WHERE id = 'm_091';
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        // Trả về đúng bộ nhãn cũ để có thể lùi lại, kể cả bộ cũ vốn đã thiếu và lệch.
        migrationBuilder.Sql(
            """
            UPDATE menu_items SET tags = ARRAY['Ha Noi', 'sang']::text[]
                WHERE id = 'm_004';
            UPDATE menu_items SET tags = ARRAY['Sai Gon', 'binh dan']::text[]
                WHERE id = 'm_006';
            UPDATE menu_items SET tags = ARRAY['mien Tay']::text[]
                WHERE id = 'm_003';
            UPDATE menu_items SET tags = ARRAY['pho bien', 'signature']::text[]
                WHERE id = 'm_001';
            UPDATE menu_items SET tags = ARRAY['chua', 'tom']::text[]
                WHERE id = 'm_005';
            UPDATE menu_items SET tags = ARRAY['chien', 'Ha Noi']::text[]
                WHERE id = 'm_002';
            UPDATE menu_items SET tags = ARRAY['cua', 'nong']::text[]
                WHERE id = 'm_007';
            UPDATE menu_items SET tags = ARRAY['cay vua', 'Hue']::text[]
                WHERE id = 'm_010';
            UPDATE menu_items SET tags = ARRAY['nuong', 'Ha Noi']::text[]
                WHERE id = 'm_011';
            UPDATE menu_items SET tags = ARRAY['mien Tay', 'dam da']::text[]
                WHERE id = 'm_013';
            UPDATE menu_items SET tags = ARRAY['cua']::text[]
                WHERE id = 'm_012';
            UPDATE menu_items SET tags = ARRAY['Ha Noi', 'nhom ban']::text[]
                WHERE id = 'm_014';
            UPDATE menu_items SET tags = ARRAY['bo', 'signature']::text[]
                WHERE id = 'm_008';
            UPDATE menu_items SET tags = ARRAY['ga']::text[]
                WHERE id = 'm_009';
            UPDATE menu_items SET tags = ARRAY['bo', 'cao cap']::text[]
                WHERE id = 'm_021';
            UPDATE menu_items SET tags = ARRAY['chien']::text[]
                WHERE id = 'm_019';
            UPDATE menu_items SET tags = ARRAY['ca', 'kho']::text[]
                WHERE id = 'm_018';
            UPDATE menu_items SET tags = ARRAY['ga', 'Hoi An']::text[]
                WHERE id = 'm_016';
            UPDATE menu_items SET tags = ARRAY['Hue']::text[]
                WHERE id = 'm_020';
            UPDATE menu_items SET tags = ARRAY['nuong', 'heo']::text[]
                WHERE id = 'm_017';
            UPDATE menu_items SET tags = ARRAY['Sai Gon', 'pho bien']::text[]
                WHERE id = 'm_015';
            UPDATE menu_items SET tags = ARRAY['cua', 'share']::text[]
                WHERE id = 'm_025';
            UPDATE menu_items SET tags = ARRAY['nuong', 'mien Tay']::text[]
                WHERE id = 'm_023';
            UPDATE menu_items SET tags = ARRAY['muc', 'cay vua']::text[]
                WHERE id = 'm_026';
            UPDATE menu_items SET tags = ARRAY['hap', 'nhau']::text[]
                WHERE id = 'm_027';
            UPDATE menu_items SET tags = ARRAY['cao cap', 'tiec']::text[]
                WHERE id = 'm_022';
            UPDATE menu_items SET tags = ARRAY['tom', 'share']::text[]
                WHERE id = 'm_024';
            UPDATE menu_items SET tags = ARRAY['rang', 'nhau']::text[]
                WHERE id = 'm_028';
            UPDATE menu_items SET tags = ARRAY['bo', '3-5 nguoi']::text[]
                WHERE id = 'm_030';
            UPDATE menu_items SET tags = ARRAY['ca', '3-5 nguoi']::text[]
                WHERE id = 'm_029';
            UPDATE menu_items SET tags = ARRAY['tiem', 'nhau']::text[]
                WHERE id = 'm_034';
            UPDATE menu_items SET tags = ARRAY['ga', 'Tay Nguyen']::text[]
                WHERE id = 'm_032';
            UPDATE menu_items SET tags = ARRAY['cay dam', 'co hai san']::text[]
                WHERE id = 'm_033';
            UPDATE menu_items SET tags = ARRAY['mien Tay', 'dam da']::text[]
                WHERE id = 'm_035';
            UPDATE menu_items SET tags = ARRAY['chay', 'nam']::text[]
                WHERE id = 'm_031';
            UPDATE menu_items SET tags = ARRAY['chien', 'tre em']::text[]
                WHERE id = 'm_038';
            UPDATE menu_items SET tags = ARRAY['hap', 'gia dinh']::text[]
                WHERE id = 'm_037';
            UPDATE menu_items SET tags = ARRAY['nuong', 'cay nhe']::text[]
                WHERE id = 'm_040';
            UPDATE menu_items SET tags = ARRAY['nuong', 'ngot']::text[]
                WHERE id = 'm_036';
            UPDATE menu_items SET tags = ARRAY['gia dinh']::text[]
                WHERE id = 'm_042';
            UPDATE menu_items SET tags = ARRAY['tiem', 'nguoi gia']::text[]
                WHERE id = 'm_041';
            UPDATE menu_items SET tags = ARRAY['xao', 'cay vua']::text[]
                WHERE id = 'm_039';
            UPDATE menu_items SET tags = ARRAY['Da Nang', 'cuon']::text[]
                WHERE id = 'm_047';
            UPDATE menu_items SET tags = ARRAY['mien Trung', 'nhau']::text[]
                WHERE id = 'm_045';
            UPDATE menu_items SET tags = ARRAY['Hoi An']::text[]
                WHERE id = 'm_044';
            UPDATE menu_items SET tags = ARRAY['Sai Gon', 'an khuya']::text[]
                WHERE id = 'm_048';
            UPDATE menu_items SET tags = ARRAY['mien Nam']::text[]
                WHERE id = 'm_046';
            UPDATE menu_items SET tags = ARRAY['mien Trung']::text[]
                WHERE id = 'm_043';
            UPDATE menu_items SET tags = ARRAY['Ha Noi', 'sang']::text[]
                WHERE id = 'm_049';
            UPDATE menu_items SET tags = ARRAY['chay', 'Hue']::text[]
                WHERE id = 'm_056';
            UPDATE menu_items SET tags = ARRAY['chay', 'giai nhiet']::text[]
                WHERE id = 'm_053';
            UPDATE menu_items SET tags = ARRAY['chay', 'chien']::text[]
                WHERE id = 'm_051';
            UPDATE menu_items SET tags = ARRAY['chay', 'healthy']::text[]
                WHERE id = 'm_052';
            UPDATE menu_items SET tags = ARRAY['chay', 'mien Trung']::text[]
                WHERE id = 'm_055';
            UPDATE menu_items SET tags = ARRAY['chay', 'nam']::text[]
                WHERE id = 'm_050';
            UPDATE menu_items SET tags = ARRAY['chay', 'dau hu']::text[]
                WHERE id = 'm_054';
            UPDATE menu_items SET tags = ARRAY['Sai Gon', 'ngot']::text[]
                WHERE id = 'm_059';
            UPDATE menu_items SET tags = ARRAY['beo']::text[]
                WHERE id = 'm_063';
            UPDATE menu_items SET tags = ARRAY['pho bien']::text[]
                WHERE id = 'm_057';
            UPDATE menu_items SET tags = ARRAY['Ha Noi', 'beo']::text[]
                WHERE id = 'm_058';
            UPDATE menu_items SET tags = ARRAY['Ha Noi', 'thanh nhe']::text[]
                WHERE id = 'm_061';
            UPDATE menu_items SET tags = ARRAY['tre em', 'ngot']::text[]
                WHERE id = 'm_062';
            UPDATE menu_items SET tags = ARRAY['giai nhiet']::text[]
                WHERE id = 'm_060';
            UPDATE menu_items SET tags = ARRAY['Sai Gon', 'binh dan']::text[]
                WHERE id = 'm_070';
            UPDATE menu_items SET tags = ARRAY['giai nhiet', 'healthy']::text[]
                WHERE id = 'm_068';
            UPDATE menu_items SET tags = ARRAY['healthy']::text[]
                WHERE id = 'm_064';
            UPDATE menu_items SET tags = ARRAY['giai nhiet']::text[]
                WHERE id = 'm_066';
            UPDATE menu_items SET tags = ARRAY['beo', 'Tay Nguyen']::text[]
                WHERE id = 'm_065';
            UPDATE menu_items SET tags = ARRAY['ngot']::text[]
                WHERE id = 'm_069';
            UPDATE menu_items SET tags = ARRAY['ngot']::text[]
                WHERE id = 'm_067';
            UPDATE menu_items SET tags = ARRAY['nuong', 'ngot']::text[]
                WHERE id = 'm_076';
            UPDATE menu_items SET tags = ARRAY['ngot', 'tre em']::text[]
                WHERE id = 'm_072';
            UPDATE menu_items SET tags = ARRAY['ngot']::text[]
                WHERE id = 'm_073';
            UPDATE menu_items SET tags = ARRAY['ngot', 'giai nhiet']::text[]
                WHERE id = 'm_071';
            UPDATE menu_items SET tags = ARRAY['ngot', 'mua lanh']::text[]
                WHERE id = 'm_075';
            UPDATE menu_items SET tags = ARRAY['giai nhiet']::text[]
                WHERE id = 'm_074';
            UPDATE menu_items SET tags = ARRAY['ngot']::text[]
                WHERE id = 'm_077';
            UPDATE menu_items SET tags = ARRAY['mien Tay']::text[]
                WHERE id = 'm_082';
            UPDATE menu_items SET tags = ARRAY['giai nhiet']::text[]
                WHERE id = 'm_081';
            UPDATE menu_items SET tags = ARRAY['beo', 'cao cap']::text[]
                WHERE id = 'm_080';
            UPDATE menu_items SET tags = ARRAY['healthy']::text[]
                WHERE id = 'm_083';
            UPDATE menu_items SET tags = ARRAY['ngot']::text[]
                WHERE id = 'm_079';
            UPDATE menu_items SET tags = ARRAY['ngot', 'healthy']::text[]
                WHERE id = 'm_084';
            UPDATE menu_items SET tags = ARRAY['healthy', 'share']::text[]
                WHERE id = 'm_078';
            UPDATE menu_items SET tags = ARRAY['nhau']::text[]
                WHERE id = 'm_085';
            UPDATE menu_items SET tags = ARRAY['nhau']::text[]
                WHERE id = 'm_086';
            UPDATE menu_items SET tags = ARRAY['nhau']::text[]
                WHERE id = 'm_087';
            UPDATE menu_items SET tags = ARRAY['nhau', 'binh dan']::text[]
                WHERE id = 'm_088';
            UPDATE menu_items SET tags = ARRAY['nhau']::text[]
                WHERE id = 'm_089';
            UPDATE menu_items SET tags = ARRAY['nhau', 'chua']::text[]
                WHERE id = 'm_090';
            UPDATE menu_items SET tags = ARRAY['ngot']::text[]
                WHERE id = 'm_091';
            """);
    }
}
