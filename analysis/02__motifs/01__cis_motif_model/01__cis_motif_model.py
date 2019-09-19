
# coding: utf-8

# In[1]:


import warnings
warnings.filterwarnings('ignore')

import itertools
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
import sys

from itertools import combinations 
from scipy.stats import boxcox
from scipy.stats import linregress
from scipy.stats import spearmanr
from scipy.stats import pearsonr
from statsmodels.stats.anova import anova_lm

from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

from scipy import stats
stats.chisqprob = lambda chisq, df: stats.chi2.sf(chisq, df)

# import utils
sys.path.append("../../../utils")
from plotting_utils import *
from classify_utils import *

get_ipython().run_line_magic('matplotlib', 'inline')
get_ipython().run_line_magic('config', "InlineBackend.figure_format = 'svg'")
mpl.rcParams['figure.autolayout'] = False


# In[2]:


sns.set(**PAPER_PRESET)
fontsize = PAPER_FONTSIZE


# In[3]:


np.random.seed(2019)


# In[4]:


QUANT_ALPHA = 0.05


# ## functions

# In[5]:


def calculate_gc(row, col):
    cs = row[col].count("C")
    gs = row[col].count("G")
    gc = (cs+gs)/len(row[col])
    return gc


# In[6]:


def calculate_cpg(row, col):
    cpgs = row[col].count("CG")
    cpg = cpgs/len(row[col])
    return cpg


# In[7]:


def lrtest(llmin, llmax):
    lr = 2 * (llmax - llmin)
    p = stats.chisqprob(lr, 1) # llmax has 1 dof more than llmin
    return lr, p


# ## variables

# In[8]:


motif_dir = "../../../data/04__mapped_motifs/elem_fimo_out"
motifs_f = "%s/fimo.txt.gz" % motif_dir


# In[9]:


elem_map_f = "../../../data/04__mapped_motifs/fastas/elem_map.txt"


# In[10]:


motif_info_dir = "../../../misc/01__motif_info"
motif_map_f = "%s/00__lambert_et_al_files/00__metadata/curated_motif_map.txt" % motif_info_dir
motif_info_f = "%s/00__lambert_et_al_files/00__metadata/motif_info.txt" % motif_info_dir


# In[11]:


sig_motifs_f = "../../../data/04__mapped_motifs/sig_motifs.txt"


# In[12]:


tss_map_f = "../../../data/01__design/01__mpra_list/mpra_tss.with_ids.UPDATED_WITH_DIV.txt"


# In[13]:


index_f = "../../../data/01__design/02__index/TWIST_pool4_v8_final.with_element_id.txt.gz"


# In[14]:


data_f = "../../../data/02__mpra/03__results/all_processed_results.txt"


# ## 1. import data

# In[15]:


index = pd.read_table(index_f, sep="\t")
index_elem = index[["element", "tile_type", "element_id", "name", "tile_number", "chrom", "strand", "actual_start", 
                    "actual_end", "dupe_info"]]
index_elem = index_elem.drop_duplicates()


# In[16]:


tss_map = pd.read_table(tss_map_f, sep="\t")
tss_map.head()


# In[17]:


motifs = pd.read_table(motifs_f, sep="\t")
motifs.head()


# In[18]:


elem_map = pd.read_table(elem_map_f, sep="\t")
elem_map.head()


# In[19]:


motif_map = pd.read_table(motif_map_f, sep="\t")
motif_map.head()


# In[20]:


motif_info = pd.read_table(motif_info_f, sep="\t")
motif_info.head()


# In[21]:


sig_motifs = pd.read_table(sig_motifs_f)
sig_motifs = sig_motifs[sig_motifs["padj"] < 0.05]
print(len(sig_motifs))
sig_motifs.head()


# In[22]:


data = pd.read_table(data_f)
data.head()


# ## 2. filter to significant motifs only (found via model)

# In[23]:


mapped_sig_motifs = motifs[motifs["#pattern name"].isin(sig_motifs["index"])]
len(mapped_sig_motifs)


# In[24]:


uniq_motifs = list(mapped_sig_motifs["#pattern name"].unique())
print(len(uniq_motifs))


# ## 3. join motifs w/ element metadata

# In[25]:


motifs_merged = mapped_sig_motifs.merge(elem_map, left_on="sequence name", right_on="elem_key")
motifs_merged.head()


# In[26]:


motifs_merged = motifs_merged.merge(index_elem, left_on="elem", right_on="element")
motifs_merged.head()


# In[27]:


motifs_merged["tss_id"] = motifs_merged["name"].str.split("__", expand=True)[1]
motifs_merged["species"] = motifs_merged["name"].str.split("_", expand=True)[0]
motifs_merged["tss_tile_num"] = motifs_merged["name"].str.split("__", expand=True)[2]
motifs_merged.sample(5)


# In[28]:


human_df = motifs_merged[(motifs_merged["species"] == "HUMAN") | (motifs_merged["name"] == "random_sequence")]
mouse_df = motifs_merged[(motifs_merged["species"] == "MOUSE") | (motifs_merged["name"] == "random_sequence")]

human_df = human_df.merge(tss_map[["hg19_id", "biotype_hg19", "cleaner_biotype_hg19", 
                                   "minimal_biotype_hg19", "stem_exp_hg19", "orig_species"]], 
                          left_on="tss_id", right_on="hg19_id", how="left")
mouse_df = mouse_df.merge(tss_map[["mm9_id", "biotype_mm9", "cleaner_biotype_mm9", 
                                   "minimal_biotype_mm9", "stem_exp_mm9", "orig_species"]], 
                          left_on="tss_id", right_on="mm9_id", how="left")

print(len(human_df))
print(len(mouse_df))
mouse_df.sample(5)


# In[29]:


human_df = human_df.drop_duplicates()
mouse_df = mouse_df.drop_duplicates()

print(len(human_df))
print(len(mouse_df))


# ## 4. merge cis data w/ element data for model

# In[30]:


index_elem = index_elem[index_elem["name"].str.contains("EVO")]
index_elem.head()


# In[31]:


index_elem["tss_id"] = index_elem["name"].str.split("__", expand=True)[1]
index_elem["tss_tile_num"] = index_elem["name"].str.split("__", expand=True)[2]
index_elem.sample(5)


# In[32]:


index_human = index_elem[index_elem["name"].str.contains("HUMAN")]
index_mouse = index_elem[index_elem["name"].str.contains("MOUSE")]
index_mouse.sample(5)


# In[33]:


print(len(data))
data_elem = data.merge(index_human[["element", "tss_id", "tss_tile_num"]], left_on=["hg19_id", "tss_tile_num"],
                       right_on=["tss_id", "tss_tile_num"])
data_elem = data_elem.merge(index_mouse[["element", "tss_id", "tss_tile_num"]], left_on=["mm9_id", "tss_tile_num"],
                            right_on=["tss_id", "tss_tile_num"], suffixes=("_human", "_mouse"))
data_elem.drop(["tss_id_human", "tss_id_mouse"], axis=1, inplace=True)
print(len(data))
data_elem.head()


# In[34]:


data_elem["gc_human"] = data_elem.apply(calculate_gc, col="element_human", axis=1)
data_elem["gc_mouse"] = data_elem.apply(calculate_gc, col="element_mouse", axis=1)
data_elem["cpg_human"] = data_elem.apply(calculate_cpg, col="element_human", axis=1)
data_elem["cpg_mouse"] = data_elem.apply(calculate_cpg, col="element_mouse", axis=1)
data_elem.sample(5)


# In[35]:


data_elem["delta_gc"] = data_elem["gc_mouse"] - data_elem["gc_human"] 
data_elem["delta_cpg"] = data_elem["cpg_mouse"] - data_elem["cpg_human"]
data_elem["mean_gc"] = data_elem[["gc_mouse", "gc_human"]].mean(axis=1)
data_elem["mean_cpg"] = data_elem[["cpg_mouse", "cpg_human"]].mean(axis=1)
data_elem["abs_delta_gc"] = np.abs(data_elem["delta_gc"])
data_elem["abs_delta_cpg"] = np.abs(data_elem["delta_cpg"])
data_elem.sample(5)


# In[36]:


data_elem["abs_logFC_cis"] = np.abs(data_elem["logFC_cis_one"])
data_elem["box_abs_logFC_cis"] = boxcox(data_elem["abs_logFC_cis"])[0]


# In[37]:


data_elem.columns


# ## 5. build reduced model

# In[38]:


scaled_features = StandardScaler().fit_transform(data_elem[["box_abs_logFC_cis", "abs_delta_gc", "abs_delta_cpg",
                                                            "mean_gc", "mean_cpg"]])
data_norm = pd.DataFrame(scaled_features, index=data_elem.index, columns=["box_abs_logFC_cis", "abs_delta_gc", 
                                                                          "abs_delta_cpg", "mean_gc", "mean_cpg"])
data_norm["HUES64_padj_hg19"] = data_elem["HUES64_padj_hg19"]
data_norm["mESC_padj_mm9"] = data_elem["mESC_padj_mm9"]
data_norm["element_human"] = data_elem["element_human"]
data_norm["element_mouse"] = data_elem["element_mouse"]
data_norm["hg19_id"] = data_elem["hg19_id"]
data_norm["mm9_id"] = data_elem["mm9_id"]
data_norm["tss_tile_num"] = data_elem["tss_tile_num"]
data_norm["cis_status_one"] = data_elem["cis_status_one"]
data_norm.head()


# In[39]:


data_filt = data_norm[((data_norm["HUES64_padj_hg19"] < QUANT_ALPHA) | (data_norm["mESC_padj_mm9"] < QUANT_ALPHA))]
print(len(data_filt))
data_filt.head()


# In[40]:


# data_filt = data_filt[data_filt["tss_tile_num"] == "tile1"].drop_duplicates()
# len(data_filt)


# In[41]:


mod = smf.ols(formula='box_abs_logFC_cis ~ mean_gc + mean_cpg + abs_delta_gc + abs_delta_cpg', 
              data=data_filt).fit()


# In[42]:


mod.summary()


# In[43]:


res = mod.resid

fig, ax = plt.subplots(figsize=(2.2, 2.2), ncols=1, nrows=1)
sm.qqplot(res, line='s', ax=ax)
ax.set_title("Normal QQ: cis effects model")
fig.savefig("avg_activ_qq.pdf", dpi="figure", bbox_inches="tight")


# In[44]:


reduced_llf = mod.llf
reduced_llf


# In[45]:


reduced_rsq = mod.rsquared
reduced_rsq


# ## 6. add motifs to model

# In[46]:


len(data_filt)


# In[47]:


data_filt["hg19_index"] = data_filt["hg19_id"] + "__" + data_filt["tss_tile_num"]
data_filt["mm9_index"] = data_filt["mm9_id"] + "__" + data_filt["tss_tile_num"]


# In[48]:


human_df["hg19_index"] = human_df["hg19_id"] + "__" + human_df["tss_tile_num"]
mouse_df["mm9_index"] = mouse_df["mm9_id"] + "__" + mouse_df["tss_tile_num"]


# In[49]:


def motif_disrupted(row):
    if row["motif_sum"] == 1:
        return "c - disrupted"
    elif row["motif_sum"] == 0:
        return "b - not present"
    else:
        return "a - maintained"


# In[50]:


motif_results = {}

for i, motif_id in enumerate(uniq_motifs):
    tmp = data_filt.copy()
    
    # determine whether motif is in human or mouse sequence
    human_motifs_sub = human_df[human_df["#pattern name"] == motif_id]["hg19_index"].unique()
    mouse_motifs_sub = mouse_df[mouse_df["#pattern name"] == motif_id]["mm9_index"].unique()
    tmp["hg19_motif"] = tmp["hg19_index"].isin(human_motifs_sub)
    tmp["mm9_motif"] = tmp["mm9_index"].isin(mouse_motifs_sub)
    
    tmp["motif_sum"] = tmp[["hg19_motif", "mm9_motif"]].sum(axis=1)
    #tmp = tmp[tmp["motif_sum"] >= 1]
    tmp["motif_disrupted"] = tmp.apply(motif_disrupted, axis=1)
    n_maintained = len(tmp[tmp["motif_disrupted"] == "a - maintained"])
    
    # make reduced model
    mod = smf.ols(formula='box_abs_logFC_cis ~ mean_gc + mean_cpg + abs_delta_gc + abs_delta_cpg', 
                  data=tmp).fit()
    reduced_llf = mod.llf
    reduced_rsq = mod.rsquared
    
    # make full model
    full_mod = smf.ols(formula='box_abs_logFC_cis ~ mean_gc + mean_cpg + abs_delta_gc + abs_delta_cpg + motif_disrupted', 
                       data=tmp).fit()
    full_llf = full_mod.llf
    full_rsq = full_mod.rsquared
    
    # perform likelihood ratio test
    lr, p = lrtest(reduced_llf, full_llf)
    
    # calculate additional variance explained
    rsq = full_rsq - reduced_rsq
    
    # record beta
    beta = list(full_mod.params)[2]
    
    # beta p
    beta_p = list(full_mod.pvalues)[2]
    
    print("(#%s) %s: n w/ motif: %s ... p: %s, rsquared: %s" % (i+1, motif_id, len(tmp), p, rsq))
    motif_results[motif_id] = {"lr_test": lr, "pval": p, "rsq": rsq, "beta": beta, "beta_p": beta_p,
                               "n_maintained": n_maintained}


# In[51]:


motif_results = pd.DataFrame.from_dict(motif_results, orient="index").reset_index()
motif_results = motif_results[motif_results["n_maintained"] >= 10]
print(len(motif_results))
motif_results.head()


# In[52]:


motif_results["padj"] = multicomp.multipletests(motif_results["pval"], method="fdr_bh")[1]
len(motif_results[motif_results["padj"] < 0.05])


# In[53]:


motif_results["beta_padj"] = multicomp.multipletests(motif_results["beta_p"], method="fdr_bh")[1]
len(motif_results[motif_results["beta_padj"] < 0.05])


# In[54]:


motif_results.sort_values(by="beta_padj").head(10)


# ## 7. join w/ TF info

# In[55]:


motif_results_mrg = motif_results.merge(sig_motifs, on="index", suffixes=("_cis", "_activ"))
motif_results_mrg.sort_values(by="padj_cis").head()


# In[56]:


#sig_results = motif_results_mrg[(motif_results_mrg["padj_cis"] < 0.05) & (motif_results_mrg["beta_cis"] > 0)]
sig_results = motif_results_mrg[(motif_results_mrg["beta_padj"] < 0.05) & (motif_results_mrg["beta_cis"] > 0)]
sig_results = sig_results.sort_values(by="beta_cis", ascending=False)


# In[57]:


pal = {"repressing": sns.color_palette("pastel")[3], "activating": sns.color_palette("pastel")[0]}


# In[58]:


full_pal = {}
for i, row in sig_results.iterrows():
    full_pal[row["HGNC symbol"]] = pal[row["activ_or_repr"]]


# In[59]:


fig = plt.figure(figsize=(4.5, 5))

ax1 = plt.subplot2grid((1, 7), (0, 0), colspan=3)
ax2 = plt.subplot2grid((1, 7), (0, 3), colspan=3)
ax3 = plt.subplot2grid((1, 7), (0, 6), colspan=1)

yvals = []
symbs = []
c = 0
for i, row in sig_results.iterrows():
    symb = row["HGNC symbol"]
    if symb not in symbs:
        yvals.append(c)
        symbs.append(symb)
        c += 1
    else:
        yvals.append(c)

sig_results["yval"] = yvals
sns.barplot(y="HGNC symbol", x="beta_cis", data=sig_results, palette=full_pal, ax=ax1)
ax1.set_ylabel("")
ax1.set_xlabel("effect size of motif disruption")

sns.barplot(y="HGNC symbol", x="rsq_activ", data=sig_results, palette=full_pal, ax=ax2)
ax2.set_ylabel("")
ax2.tick_params(left=False, labelleft=False)
ax2.set_xlabel("additional variance explained")

melt = pd.melt(sig_results, id_vars=["HGNC symbol", "yval"], value_vars=["no_CAGE_enr", "eRNA_enr",
                                                                                 "lncRNA_enr", "mRNA_enr"])
ax3.plot(melt["value"], melt["yval"], 'o', color="black")
ax3.set_xlim((-0.5, 3.5))
ax3.set_ylim((np.max(yvals)-0.5, -0.5))
ax3.tick_params(labelleft=False, labelbottom=False, bottom=False, left=False, top=True, labeltop=True)
ax3.xaxis.set_ticks([0, 1, 2, 3])
ax3.set_xticklabels(["no CAGE", "eRNA", "lncRNA", "mRNA"], rotation=60, ha="left", va="bottom")

plt.show()
fig.savefig("cis_motif_enrichment.pdf", dpi="figure", bbox_inches="tight")
plt.close()


# In[60]:


data_filt = data_elem[((data_elem["HUES64_padj_hg19"] < QUANT_ALPHA) | (data_elem["mESC_padj_mm9"] < QUANT_ALPHA))]
print(len(data_filt))
# data_filt = data_filt[data_filt["tss_tile_num"] == "tile1"].drop("orig_species", axis=1).drop_duplicates()
# len(data_filt)


# In[61]:


data_filt["hg19_index"] = data_filt["hg19_id"] + "__" + data_filt["tss_tile_num"]
data_filt["mm9_index"] = data_filt["mm9_id"] + "__" + data_filt["tss_tile_num"]


# In[62]:


def uniq_motif(row):
    if row.hg19_motif == True:
        if row.mm9_motif == True:
            return "maintained"
        else:
            return "disrupted in mouse"
    else:
        if row.mm9_motif == True:
            return "disrupted in human"
        else:
            return "not present"


# In[63]:


sns.palplot(sns.color_palette("Set2"))


# In[64]:


# plot some examples
examps = ["ZNF524", "ASCL2", "ASCL1", "FOS", "NFYB", "ETV1", "GABPA"]
order1 = ["b - not present", "a - maintained", "c - disrupted"]
order2 = ["maintained", "disrupted in human", "disrupted in mouse"]
pal1 = {"b - not present": "lightgray", "a - maintained": "darkgray", "c - disrupted": sns.color_palette("Set2")[2]}
pal2 = {"maintained": "darkgray", "disrupted in human": sns.color_palette("Set2")[1], 
        "disrupted in mouse": sns.color_palette("Set2")[0]}

for symb in examps:
    motif_id = sig_results[sig_results["HGNC symbol"] == symb]["index"].iloc[0]
    
    tmp = data_filt.copy()
    
    # determine whether motif is in human or mouse sequence
    human_motifs_sub = human_df[human_df["#pattern name"] == motif_id]["hg19_index"].unique()
    mouse_motifs_sub = mouse_df[mouse_df["#pattern name"] == motif_id]["mm9_index"].unique()
    tmp["hg19_motif"] = tmp["hg19_index"].isin(human_motifs_sub)
    tmp["mm9_motif"] = tmp["mm9_index"].isin(mouse_motifs_sub)
    
    tmp["motif_sum"] = tmp[["hg19_motif", "mm9_motif"]].sum(axis=1)
    #tmp = tmp[tmp["motif_sum"] >= 1]
    tmp["motif_disrupted"] = tmp.apply(motif_disrupted, axis=1)
    tmp["uniq_motif"] = tmp.apply(uniq_motif, axis=1)
    
    fig, axarr = plt.subplots(figsize=(4, 1.5), nrows=1, ncols=2)
    
    ax = axarr[0]
    sns.boxplot(data=tmp, x="motif_disrupted", y="abs_logFC_cis", order=order1, palette=pal1, 
                flierprops = dict(marker='o', markersize=5), ax=ax)
    mimic_r_boxplot(ax)
    ax.set_xticklabels(["motif not present", "motif maintained", "motif disrupted"], rotation=50, 
                       ha="right", va="top")
    ax.set_ylabel("| assigned cis effect size |")
    ax.set_title(symb)
    ax.set_xlabel("")
    
    for i, label in enumerate(order1):
        n = len(tmp[tmp["motif_disrupted"] == label])
        ax.annotate(str(n), xy=(i, -0.9), xycoords="data", xytext=(0, 0), 
                    textcoords="offset pixels", ha='center', va='top', 
                    color=pal1[label], size=fontsize)

    ax.set_ylim((-1.7, 6))

    ax = axarr[1]
    sns.boxplot(data=tmp, x="uniq_motif", y="logFC_cis_one", order=order2, palette=pal2,
                flierprops = dict(marker='o', markersize=5), ax=ax)
    ax.set_xticklabels(order2, rotation=50, ha="right", va="top")
    mimic_r_boxplot(ax)
    ax.set_ylabel(" assigned cis effect size")
    ax.set_title(symb)
    ax.set_xlabel("")
    ax.axhline(y=0, linestyle="dashed", color="black", zorder=100)
    
    for i, label in enumerate(order2):
        n = len(tmp[tmp["uniq_motif"] == label])
        ax.annotate(str(n), xy=(i, -6.5), xycoords="data", xytext=(0, 0), 
                    textcoords="offset pixels", ha='center', va='top', 
                    color=pal2[label], size=fontsize)
        
    # calc p-vals b/w dists
    dist1 = np.asarray(tmp[tmp["uniq_motif"] == "maintained"]["logFC_cis_one"])
    dist2 = np.asarray(tmp[tmp["uniq_motif"] == "disrupted in human"]["logFC_cis_one"])
    dist3 = np.asarray(tmp[tmp["uniq_motif"] == "disrupted in mouse"]["logFC_cis_one"])

    dist1 = dist1[~np.isnan(dist1)]
    dist2 = dist2[~np.isnan(dist2)]
    dist3 = dist3[~np.isnan(dist3)]

    u, pval1 = stats.mannwhitneyu(dist1, dist2, alternative="two-sided", use_continuity=False)
    u, pval2 = stats.mannwhitneyu(dist1, dist3, alternative="two-sided", use_continuity=False)
    print(pval1)
    print(pval2)

#     annotate_pval(ax, 0.2, 0.8, 3, 0, 3, pval1, fontsize)
#     annotate_pval(ax, 0.2, 1.8, 4, 0, 4, pval2, fontsize)

    ax.set_ylim((-8, 6))
    
    plt.subplots_adjust(wspace=0.4)
    plt.show()


# ## 8. for every sequence pair, calculate the # identical motifs, the # motifs that fully turn over, and the # motifs that partially turn over
# 
# defined as:
# - identical motifs = identical sequence in both species
# - full turnover = motifs that are only present in one species
# - partial turnover = motifs that are in both species but don't map to the exact same sequence

# In[65]:


print(len(data))
data.head()


# In[66]:


turnover_results = {}

for i, row in data.iterrows():
    if i % 100 == 0:
        print("...# %s..." % (i+1))

    human_id = row["hg19_id"]
    mouse_id = row["mm9_id"]
    tile_num = row["tss_tile_num"]
    
    human_motifs_sub = human_df[(human_df["hg19_id"] == human_id) & (human_df["tss_tile_num"] == tile_num)]
    mouse_motifs_sub = mouse_df[(mouse_df["mm9_id"] == mouse_id) & (mouse_df["tss_tile_num"] == tile_num)]
    
    # find total number of unique motifs (in both species)
    human_motif_ids = list(human_motifs_sub["#pattern name"].unique())
    mouse_motif_ids = list(mouse_motifs_sub["#pattern name"].unique())
    total_uniq_motifs = len(set(human_motif_ids + mouse_motif_ids))
    
    # find difference in motifs b/w the two species
    delta_motifs = len(mouse_motif_ids) - len(human_motif_ids)
    
    # find number of motifs that are in both species
    merge_sub = human_motifs_sub[["#pattern name", 
                                  "matched sequence"]].merge(mouse_motifs_sub[["#pattern name", 
                                                                               "matched sequence"]],
                                                             on="#pattern name",
                                                             suffixes=(" human", " mouse"))
    merge_sub = merge_sub.drop_duplicates()
    
    # find number of motifs that are *exactly the same* in both species
    merge_sub["identical"] = merge_sub["matched sequence human"] == merge_sub["matched sequence mouse"]
    
    # since there can be more than one occurrence of the same motif: 
    # if there is at least 1 instance of an identical motif, call it identical
    # otherwise, call it partial
    # to do this, sort the df and keep the first occurrence (which will always = True if it's there)
    merge_sub = merge_sub.sort_values(by=["#pattern name", 
                                          "identical"], ascending=False)[["#pattern name", "identical"]]
    merge_sub = merge_sub.drop_duplicates(subset="#pattern name")
    total_in_both = len(merge_sub)
    
    n_identical = len(merge_sub[merge_sub["identical"]])
    
    # find number that are partially different
    n_partial = len(merge_sub[~merge_sub["identical"]])
    
    # find number of motifs that fully turn over between species (i.e. are in only one species)
    n_human_uniq = len(set(human_motif_ids).difference(set(mouse_motif_ids)))
    n_mouse_uniq = len(set(mouse_motif_ids).difference(set(human_motif_ids)))
    n_turnover = n_human_uniq + n_mouse_uniq
    
    turnover_results["%s__%s__%s" % (human_id, mouse_id, tile_num)] = {"total_motifs": total_uniq_motifs,
                                                                       "total_shared_motifs": total_in_both,
                                                                       "n_identical_motifs": n_identical,
                                                                       "n_partial_motifs": n_partial,
                                                                       "n_turnover_motifs": n_turnover,
                                                                       "delta_motifs": delta_motifs}


# In[67]:


turnover_df = pd.DataFrame.from_dict(turnover_results, orient="index").reset_index()

# split index column to separate id columns
turnover_df["hg19_id"] = turnover_df["index"].str.split("__", expand=True)[0]
turnover_df["mm9_id"] = turnover_df["index"].str.split("__", expand=True)[1]
turnover_df["tss_tile_num"] = turnover_df["index"].str.split("__", expand=True)[2]

# calculate percentages
turnover_df["perc_shared_motifs"] = (turnover_df["total_shared_motifs"]/turnover_df["total_motifs"])*100
turnover_df["perc_identical_motifs"] = (turnover_df["n_identical_motifs"]/turnover_df["total_shared_motifs"])*100
turnover_df["perc_partial_motifs"] = (turnover_df["n_partial_motifs"]/turnover_df["total_shared_motifs"])*100
turnover_df["perc_turnover_motifs"] = (turnover_df["n_turnover_motifs"]/turnover_df["total_motifs"])*100
turnover_df["abs_delta_motifs"] = np.abs(turnover_df["delta_motifs"])

turnover_df.head()


# ## 9. merge motif turnover data w/ cis effects

# In[68]:


data_motifs = data.merge(turnover_df, on=["hg19_id", "mm9_id", "tss_tile_num"], how="left")
print(len(data_motifs))
data_motifs.head()


# ## 6. filter data

# In[69]:


data_filt = data_motifs[((data_motifs["HUES64_padj_hg19"] < QUANT_ALPHA) | (data_motifs["mESC_padj_mm9"] < QUANT_ALPHA))]
len(data_filt)


# In[70]:


data_filt_sp = data_filt.drop("orig_species", axis=1)
data_filt_sp.drop_duplicates(inplace=True)
len(data_filt_sp)


# In[71]:


data_filt_tile1 = data_filt[data_filt["tss_tile_num"] == "tile1"]
len(data_filt_tile1)


# In[72]:


data_filt_tile1_sp = data_filt_sp[data_filt_sp["tss_tile_num"] == "tile1"]
len(data_filt_tile1_sp)


# In[73]:


data_filt_tile2 = data_filt[data_filt["tss_tile_num"] == "tile2"]
len(data_filt_tile2)


# In[74]:


data_filt_tile2_sp = data_filt_sp[data_filt_sp["tss_tile_num"] == "tile2"]
len(data_filt_tile2_sp)


# ## 7. plot cis effects v motif turnover

# In[75]:


dfs = [data_filt_sp, data_filt_tile1_sp, data_filt_tile2_sp]
titles = ["both tiles", "tile1 only", "tile2 only"]
labels = ["both_tiles", "tile1_only", "tile2_only"]


# In[76]:


order = ["no cis effect", "significant cis effect"]
palette = {"no cis effect": "gray", "significant cis effect": sns.color_palette("Set2")[2]}


# ### % shared motifs

# In[77]:


for df, title, label in zip(dfs, titles, labels):
    
    fig = plt.figure(figsize=(1.25, 2))
    ax = sns.boxplot(data=df, x="cis_status_one", y="perc_shared_motifs", palette=palette, order=order,
                     flierprops = dict(marker='o', markersize=5))
    mimic_r_boxplot(ax)
    
    ax.set_xticklabels(["no cis effect", 'cis effect'], rotation=50, ha='right', va='top')
    ax.set_xlabel("")
    ax.set_ylabel("% shared motifs")
    ax.set_title(title)
    
    for i, l in enumerate(order):
        n = len(df[df["cis_status_one"] == l])
        ax.annotate(str(n), xy=(i, -5), xycoords="data", xytext=(0, 0), 
                    textcoords="offset pixels", ha='center', va='top', 
                    color=palette[l], size=fontsize)

    ax.set_ylim((-18, 100))
    
    # calc p-vals b/w dists
    dist1 = np.asarray(df[df["cis_status_one"] == "no cis effect"]["perc_shared_motifs"])
    dist2 = np.asarray(df[df["cis_status_one"] != "no cis effect"]["perc_shared_motifs"])

    dist1 = dist1[~np.isnan(dist1)]
    dist2 = dist2[~np.isnan(dist2)]

    u, pval = stats.mannwhitneyu(dist1, dist2, alternative="two-sided", use_continuity=False)
    print(pval)

    annotate_pval(ax, 0.2, 0.8, 55, 0, 52, pval, fontsize)
    
    plt.show()
    fig.savefig("cis_effect_v_shared_motifs.%s.pdf" % label, dpi="figure", bbox_inches="tight")
    plt.close()


# ## 8. plot motif #s across biotypes

# In[78]:


def turnover_status(row):
    if "CAGE turnover" in row["biotype_switch_minimal"]:
        return "CAGE turnover"
    else:
        return "none"
    
def turnover_biotype(row):
    if "CAGE turnover" in row["biotype_switch_minimal"]:
        return row["biotype_switch_minimal"].split(" - ")[1]
    else:
        return row["biotype_switch_minimal"]


# In[79]:


turnover_order = ["eRNA", "lncRNA", "mRNA"]
turnover_pal = {"CAGE turnover": "gray", "none": sns.color_palette("Set2")[2]}
hue_order = ["CAGE turnover", "none"]


# In[80]:


for df, title, label in zip(dfs, titles, labels):
    df["turnover_status"] = df.apply(turnover_status, axis=1)
    df["turnover_biotype"] = df.apply(turnover_biotype, axis=1)
    
    fig = plt.figure(figsize=(2.5, 2))
    ax = sns.boxplot(data=df, x="turnover_biotype", y="perc_shared_motifs", hue="turnover_status",
                     flierprops = dict(marker='o', markersize=5), 
                     order=turnover_order, hue_order=hue_order, palette=turnover_pal)
    mimic_r_boxplot(ax)

    ax.set_xticklabels(turnover_order, rotation=50, ha='right', va='top')
    ax.set_xlabel("")
    ax.set_ylabel("% shared motifs")
    ax.set_title(title)

    for i, l in enumerate(turnover_order):
        sub = df[df["turnover_biotype"] == l]
        dist1 = np.asarray(sub[sub["turnover_status"] == "CAGE turnover"]["perc_shared_motifs"])
        dist2 = np.asarray(sub[sub["turnover_status"] == "none"]["perc_shared_motifs"])
        
        dist1 = dist1[~np.isnan(dist1)]
        dist2 = dist2[~np.isnan(dist2)]
        
        u, pval = stats.mannwhitneyu(dist1, dist2, alternative="two-sided", use_continuity=False)
        ymax = np.max(dist2)
        
        if pval >= 0.05:
            annotate_pval(ax, i-0.1, i+0.1, ymax, 0, ymax, pval, fontsize)
        else:
            annotate_pval(ax, i-0.1, i+0.1, ymax, 0, ymax-4, pval, fontsize)
            
        ax.annotate(str(len(dist1)), xy=(i-0.25, -9), xycoords="data", xytext=(0, 0), 
                    textcoords="offset pixels", ha='center', va='bottom', 
                    color="gray", size=fontsize)
        ax.annotate(str(len(dist2)), xy=(i+0.25, -9), xycoords="data", xytext=(0, 0), 
                    textcoords="offset pixels", ha='center', va='bottom', 
                    color=sns.color_palette("Set2")[2], size=fontsize)

    ax.set_ylim((-11, 100))
    plt.legend(loc=2, bbox_to_anchor=(1.1, 1))
    plt.show()
    fig.savefig("shared_motifs_biotypes.%s.pdf" % label, dpi="figure", bbox_inches="tight")
    plt.close()


# ## 11. write motif files

# In[81]:


len(human_df)


# In[82]:


len(mouse_df)


# In[83]:


human_f = "../../../data/04__mapped_motifs/human_motifs_filtered.txt.gz"
human_df.to_csv(human_f, sep="\t", index=False, compression="gzip")


# In[84]:


mouse_f = "../../../data/04__mapped_motifs/mouse_motifs_filtered.txt.gz"
mouse_df.to_csv(mouse_f, sep="\t", index=False, compression="gzip")
