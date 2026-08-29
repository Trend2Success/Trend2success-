from dfs_ev.scoring.ncaaf_dk import DK_CFB_CLASSIC_SCORING, ScoringConfig, StatLine, score_stat_line


def test_passing_yards_and_td_and_bonus():
    stats = StatLine(pass_yards=310, pass_tds=3, interceptions=1)
    pts = score_stat_line(stats)
    # 310*0.04 + 3*4 + 1*(-1) + 3 (300yd bonus) = 12.4 + 12 - 1 + 3 = 26.4
    assert pts == 26.4


def test_rushing_yards_and_td_and_bonus():
    stats = StatLine(rush_yards=120, rush_tds=2)
    pts = score_stat_line(stats)
    # 120*0.1 + 2*6 + 3 (100yd bonus) = 12 + 12 + 3 = 27.0
    assert pts == 27.0


def test_non_ppr_default_zeroes_out_receptions():
    stats = StatLine(receptions=6, rec_yards=40)
    pts = score_stat_line(stats)
    assert pts == 4.0  # 40 * 0.1, receptions worth 0 by default


def test_ppr_config_scores_receptions():
    ppr = ScoringConfig(reception_pt=1.0)
    stats = StatLine(receptions=6, rec_yards=40)
    pts = score_stat_line(stats, config=ppr)
    assert pts == 10.0  # 6*1 + 40*0.1


def test_fumble_lost_and_two_point_conversion():
    stats = StatLine(fumbles_lost=1, two_pt_conversions=1)
    pts = score_stat_line(stats)
    assert pts == 1.0  # -1 + 2


def test_kicker_scoring_only_used_when_relevant():
    stats = StatLine(fg_made_0_39=2, fg_made_40_49=1, fg_made_50_plus=1, extra_points_made=3)
    pts = score_stat_line(stats)
    assert pts == 2 * 3.0 + 4.0 + 5.0 + 3 * 1.0


def test_below_bonus_threshold_no_bonus():
    stats = StatLine(pass_yards=299, pass_tds=0)
    pts = score_stat_line(stats)
    assert pts == round(299 * 0.04, 2)


def test_default_config_is_the_module_constant():
    assert DK_CFB_CLASSIC_SCORING.pass_td_pt == 4.0
    assert DK_CFB_CLASSIC_SCORING.rush_td_pt == 6.0
    assert DK_CFB_CLASSIC_SCORING.rec_td_pt == 6.0
